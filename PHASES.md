# PHASES: Build Order

How the system gets built. Each phase **builds one ring of the
[architecture](ARCHITECTURE.md), test-first, owned by the test tier that ring is
assigned to.** Decisions behind the choices are D1–D27 in [`PLAN.md`](PLAN.md).

> **This is a living plan.** Nothing here is fixed. Decisions, phase boundaries,
> and deliverables can be changed, reordered, or dropped the moment a better
> requirement or design surfaces, **changeability is a core goal of this
> system, and that applies to the plan itself.** Revising this document as we
> learn is *using* the architecture, not deviating from it. The invariants we
> hold across any change: the Dependency Rule, ports with paired real+fake
> adapters, the three test tiers mapped to the layers, and a live enforcement
> gate. Change freely above that line; keep those four.

## How every phase runs (the philosophy, applied)

1. **Red before green.** New behaviour starts as a *failing* test in the tier
   that owns its layer. Then it's made to pass. Then `make check` runs every tier.
2. **One ring at a time, inward-out.** We build the cheap, pure core first and
   move outward toward the costly edges. A ring is "done" only when its tier is
   green *and* the enforcement gate accepts it.
3. **Fakes before real.** A port's fake and its conformance suite come before its
   real adapter, so the inner rings are testable with zero infrastructure the
   whole way up.
4. **The gate grows with the code.** `make guard` and the structural
   test-doctrine checks are live from Phase 0, so a boundary can never be
   silently crossed.
5. **Assume a hostile, careless public, not a careful researcher.** This system
   is used by random everyday users, not by us. Every layer's tests must cover the
   dumb, the malformed, and the adversarial: legs that are empty / reversed / out
   of order / off the route, station pairs that are reversed or identical, dates in
   the past or beyond the booking window or simply not a date, trains asked for on a
   weekday they do not run, negative or fractional passenger counts, double-clicks
   and duplicate submits, holding an already-held or already-expired seat,
   confirming after expiry, cancelling twice, integer/money overflow, absurd
   quantities, unicode/oversized strings, missing or extra fields, and races where
   two users fight over one seat. **The happy path is the easy 10%; the edge cases
   are the test suite.** Invalid input must fail loud and safe (typed error → clean
   4xx), never corrupt state. Property tests (Hypothesis / fast-check) exist partly
   to *generate* the dumb input we wouldn't think to write by hand.

| Phase | Ring built | Test tier that owns it |
|---|---|---|
| P0 | (none, the enforcement + infra spine) | arch gate + `guard` |
| P1 | Backend **L0 domain** | **unit** |
| P2 | Backend **L1 ports** + **L2 fakes** | **integration** (fakes) |
| P3 | Backend **L2 real adapters** | **integration** (real Postgres) |
| P4 | Backend **L3 use-cases** | **integration** (fakes + thin real) |
| P5 | Backend **L4 composition root** | **contract** + thin **system** |
| P6a | Frontend **L0→L4** (first cut) | **unit** + **integration** + **contract** |
| P4b | Backend **L0+L3 revision** (timetable, waitlist out, counter sale, receipt) | **unit** + **integration** (fakes) |
| P5b | Backend **L4 revision** (contract, routes, seeder) | **contract** + thin **system** |
| P6c | Frontend **L0→L4** (traveller app, rebuilt) | **unit** + **integration** + **contract** |
| P6b | Frontend **admin counter app** | **unit** + **integration** + **contract** |
| P7 | Whole system | **system** (E2E) |
| P8 | Seed & config realism | one-command bring-up |
| P9 | Docs & polish | none |

**P0–P6a, P4b, P5b, P6c, P7 and P8 are built.** The remaining order is **P6b → P9**;
P6b (admin counter app) was pushed after P7/P8 since it's the one piece not on the
traveller's critical path, and P9 (docs/polish) is out of scope for now.

---

## P0: Rails (the spine that makes everything else test-driven)

Builds no ring; installs the machinery every ring depends on. **This comes first
because test-drivenness and enforcement are infrastructure, not habits.**

**Deliverables**
- Repo tree per [ARCHITECTURE.md](ARCHITECTURE.md); empty `__init__.py` per layer.
- `pyproject.toml` (ruff, mypy, pytest markers: `unit`/`integration`/`concurrency`/`contract`/`arch`), `web/` Vite+**Svelte**+JS+Vitest+ESLint+dependency-cruiser.
- `.importlinter` with the four contracts; `tests/architecture/` source-scan + test-doctrine checks (they pass trivially on an empty tree and tighten as code lands).
- `docker-compose.yml`: `db` (Postgres, healthcheck), `migrate`, `seed`, `api`, `web`; profiles `test` and `e2e`. `.env.example` with working local defaults.
- `Makefile`: `check`, `lint`, `arch`, `test:unit|int|e2e`, `guard`, `demo-concurrency`, `demo-resale`.
- GitHub Actions: one lean job running `make guard` + `make check` on push/PR. E2E is deferred to P7 (kept as a commented, non-blocking stub, it's the flaky part).

**Exit gate**, `make guard` plants `slr/domain/_guard.py: import sqlalchemy`,
import-linter **rejects it**, cleanup runs. `make check` is green on the empty
tree. `docker compose up` starts and healthchecks pass.

---

## P1: Backend L0 domain (pure) · tier: UNIT

The correctness-critical core, built entirely test-first. No I/O, no framework,
no clock, the source scan enforces it.

**Deliverables** (each lands as failing unit tests first)
- `stations.py`, `Station`, `Leg` as half-open interval over station sequence; `overlaps`, `is_adjacent`, `contains`, `distance_km`. **Hypothesis property tests**: overlap is symmetric; adjacent legs never overlap; no-overlap ⇔ resellable.
- `fares.py`, `Money` (LKR minor units); `distance_fare`; `dynamic_fare(occupancy)`. **Oracle tests** against hand-computed fares (incl. the derived Kandy-leg example from PLAN §7).
- `packing.py`, interval-partition optimizer (min seats), best-seat selection (maximise future contiguous seat-km), `impact_seat_km`. **Property + optimality tests**: never assigns overlapping legs to one seat; result ≤ naive; matches greedy optimum.
- `booking_sm.py`, status transitions + guards. Tests: illegal transitions raise; expiry frees.
- `policy.py`, `within_seat_cap`, `within_velocity`, `named_passenger_ok` as pure predicates over (events, now). Tests cover boundaries.
- `abuse.py`, heuristic score (pure). `values.py`, `errors.py`.

**Exit gate**, every `domain/` module has a unit test (test-doctrine check
asserts it); property/oracle suites green; source scan confirms zero I/O/clock/rng.

---

## P2: Backend L1 ports + L2 fakes · tier: INTEGRATION (fakes)

Define every seam to the costly world and its deterministic stand-in. **The fakes
and their conformance suites exist before any real adapter**, so L3/L4 are
testable without infrastructure.

**Deliverables**
- All port Protocols in `slr/ports/` (see [ARCHITECTURE.md](ARCHITECTURE.md#ports)).
- In-memory fakes for each; **`memory_repo.py` replicates the overlap invariant** (rejects overlapping active holds for the same trip+seat).
- **One conformance suite per port** in `tests/integration/ports/`, run against the fake now (and, unchanged, against the real adapter in P3). The booking-repo suite pins overlap/adjacency, hold expiry, and cancellation-frees-segment.

**Exit gate**, every port has a conformance suite (test-doctrine check);
all fakes pass; `usecases` can already be written against these interfaces.

---

## P3: Backend L2 real adapters · tier: INTEGRATION (real Postgres)

Make the seams real. The proof of concurrency correctness lands here.

**Deliverables**
- SQLAlchemy 2.0 models + Alembic migrations, including `CREATE EXTENSION btree_gist` and the partial `EXCLUDE USING gist (trip_id =, seat_id =, leg &&) WHERE status IN ('HELD','CONFIRMED')`.
- `sqlalchemy_repo.py`, translates the DB `IntegrityError` → `OverlapError`; retires expired holds lazily inside the booking transaction (D12).
- Real `system_clock`, `uuid_ids`, `mock_payment`, `log_notifier`, `heuristic_abuse`, `distance_fare`/`dynamic_fare`, `sse_publisher`, `env_config`.
- **The same P2 conformance suites now run against the real adapters** via Testcontainers-Postgres.
- **Concurrency-proof test** (`tests/integration/concurrency/`): N simultaneous `add_hold` on one seat/leg → exactly one commits, N−1 raise `OverlapError`; adjacent legs both commit.

**Exit gate**, real adapters pass the *identical* conformance suites the fakes
passed; concurrency proof green; `make demo-concurrency` prints "1 booked, N−1 got 409".

---

## P4: Backend L3 use-cases · tier: INTEGRATION (all-fake, thin real)

Orchestrate intents through ports only. Written and tested against **all-fake**
adapters (fast, deterministic), so concurrency/error semantics are pinned without
infrastructure; a thin real pass covers `hold`/`confirm`.

**Deliverables**, `search_trips`, `leg_availability`, `quote_fare`,
`hold_seat` (reserved: validate leg → caps/velocity/abuse → requested seat →
`add_hold` → idempotency), `book_unreserved`, `settle_at_counter`,
`lookup_booking`, `confirm_booking` (reserved online payment → transition),
`cancel_booking`, `join_waitlist`, `promote_waitlist`, `impact_report`.

> **Revised by P4b.** The waitlist use-cases are withdrawn (D16), `search_trips`
> becomes `search_trains(origin, dest, date)` (D22), and
> `book_unreserved`+`settle_at_counter` collapse into one counter intent (D23).

**Exit gate**, every use-case has a fake-based test (test-doctrine check);
error paths (cap exceeded, overlap→409, payment declined, expired hold) covered;
`usecases` imports no adapter and no framework (import-linter).

---

## P5: Backend L4 composition root · tier: CONTRACT + thin SYSTEM

Wire real adapters into use-cases and expose HTTP. **The only code no inner tier
exercises directly.**

**Deliverables**, FastAPI `main.py` + `wiring.py` (real adapters injected),
`config.py`, `schemas.py` (Pydantic = the **contract source**), `routes/`
(trips, availability, `bookings` hold→confirm→cancel, waitlist, **SSE** stream,
`admin` lookup + settle behind a shared counter key), `middleware/idempotency.py`,
`errors.py` (Overlap→409, Cap→429, Invalid→422), OpenAPI emitted to `contract/`.

**Exit gate**, OpenAPI generated; contract tests assert routes emit the schema;
app boots in compose behind a healthcheck; a thin API-level system test books a seat end-to-end.

> **Revised by P5b.** Waitlist routes, `/unreserved` and the public
> `GET /bookings/{reference}` are removed; trips gain train identity, times and
> coach layouts; the admin router gains sell + verify.

---

## P6a: Frontend hexagon, first cut · tier: UNIT + INTEGRATION + CONTRACT

Same layering, mirrored. Built inward-out: view-core → ports → fake client → real
client → UI → shell.

> **Replaced by P6c.** The hexagon (view-core → ports → adapters → ui → app) and
> its contract seam survive; the screens are rebuilt around the landing page,
> journey search, train list, coach switcher and receipt (D26). The waitlist and
> unreserved modes come out (D16, D23).

**Deliverables**
- `view-core/` (unit): `legs`, `availability` (which seats are free for a leg), `seatmap` (layout model), `fares` (format), `booking` (hold-flow reducer). Vitest.
- `ports/` + `adapters/`: `api-client.fake` first (drives component tests), then `api-client.real` (JS client generated from `contract/`, responses validated against the OpenAPI schema at runtime); `availability-stream.real` (`EventSource`) + fake; `storage.*`.
- `ui/` (integration on the fake client): `RoutePicker`, `DatePicker`, **`SeatMap`** (per-leg availability colouring, click-to-hold), `HoldTimer`, `ConfirmForm`, `WaitlistButton`; optimistic UI with graceful **409** handling; live grey-out via SSE.
- `app/` shell, router, providers, env, real-adapter injection.

**Exit gate**, view-core modules unit-tested; components tested on the fake
`ApiClient`; contract test validates the real client's responses against the
OpenAPI schema at runtime (no FE compiler, this is what holds the seam);
dependency-cruiser passes (no `fetch` outside `adapters/`).

---

## P4b: Domain + use-case revision · tier: UNIT + INTEGRATION (fakes)

Four changes land together because they share one contract shape: the timetable
becomes real, the waitlist goes, unreserved moves to the counter, and every paid
booking produces a receipt. **Red before green still applies**, each item starts
as a failing test in the tier that owns its layer.

**Deliverables**

*Withdraw the waitlist (D16).* Delete `usecases/join_waitlist.py`,
`usecases/promote_waitlist.py`, `usecases/_promote.py`, `WaitlistEntry` /
`WaitlistRepository` / `UnitOfWork.waitlist` from `ports/repository.py`, the
waitlist halves of `memory_repo.py` and `sqlalchemy_repo.py`, `WaitlistRow` from
`orm.py`, and the `waitlist` table from the initial migration. `cancel_booking`
loses its promotion step, `CancelResult.promoted` goes with it. Tests
`test_join_waitlist.py` and `test_promote_waitlist.py` are deleted and the
repository conformance suite drops its waitlist section. *Nothing is deprecated
in place, a withdrawn decision leaves no dead code.*

*Timetable (D22), `domain/timetable.py`, pure and unit-tested first:*
`runs_on(days_of_week, service_date)` (weekday arithmetic over an ISO date, no
clock), `serves(stops, origin_seq, dest_seq)` (both stops present, origin before
destination), `leg_times(stops, leg)` → depart/arrive offsets and duration,
`materialize(pattern, service_date)` → the `Trip` record. Property tests: a
pattern appears on exactly the weekdays it declares; `serves` is false for
reversed or off-route pairs; duration is monotone in leg length.

*`search_trains(origin_code, dest_code, service_date)` (L3)*, replaces
`search_trips`. Resolves the two station codes, asks the trip repo for that date,
filters by `serves`, and returns per train: identity (number + name), depart and
arrive time **for that leg**, duration, free seats per class over the leg, and a
from-fare. Fake-adapter tests cover: a train that does not run that weekday is
absent; a train that skips the origin is absent; a reversed pair returns empty; a
date outside the booking window is a typed error, not an empty list.

*`sell_unreserved` (L3, D23)*, one counter transaction: caps/velocity/abuse on
the NIC → create the booking → `choose_seat` (packing) or standing under
`standing_capacity` (D20) → charge cash → `CONFIRMED`/`STANDING` → receipt.
Replaces `book_unreserved` + `settle_at_counter`. Tests: seat assigned when one
fits; standing prediction when none does; `CoachFull` past capacity; a declined
charge leaves **no** booking behind.

*`verify_ticket(reference)` (L3, D21)*, read-only. Returns the booking with the
passenger NIC, train, leg, coach/seat or standing, status, and a verdict
(`VALID` / `NOT_FOUND` / `CANCELLED` / `EXPIRED` / `WRONG_DAY`). Never mutates.

*`receipt` (D24)*, one assembly shared by `confirm_booking` and
`sell_unreserved`: reference, passenger, train identity, date, leg with times,
coach/seat or standing prediction, fare, issued-at, and the QR payload (the bare
reference). Unit-tested as a pure builder over a booking + trip.

*Seat geometry (D25)*, coach layouts (rows, columns, exit rows) flow from config
onto the `Trip` record so the contract can carry them.

**Exit gate**, every new domain module has a unit test and every use-case a
fake-based test (the doctrine check enforces both); no `waitlist` symbol survives
anywhere in `backend/` or `tests/`; `make check` green.

---

## P5b: Contract + routes revision · tier: CONTRACT + thin SYSTEM

**Deliverables**
- **Removed routes:** `POST /unreserved`, every `/waitlist*` route, and the
  public `GET /bookings/{reference}` (D24, it leaks a passenger's NIC to anyone
  who guesses a reference; the counter-key route stays).
- **Changed schemas:** `TripOut` gains `train_no`, `train_name`, `stops[]`
  (station seq + arrive/depart) and `coaches[]` (code, type, class, rows,
  columns, exit rows). New `TrainSearchOut` (one row per train, with leg times,
  duration, per-class free counts, from-fare) and `ReceiptOut`. `CancelOut` drops
  `promoted`. `WaitlistOut`/`WaitlistRequest`/`PromoteRequest` deleted.
- **New routes:** `GET /search?origin=&dest=&date=` → `TrainSearchOut[]`;
  `POST /bookings/{id}/confirm` now returns `ReceiptOut`; admin
  `POST /admin/unreserved/sell` → `ReceiptOut` and
  `GET /admin/verify/{reference}` → `VerifyOut`, both behind the counter key.
- **Seeder (D22):** service patterns + coach layouts in config; a compose step
  expands them across `booking_window_days` into dated trips, idempotent on
  `{pattern_code}:{date}`. This retires the `demo_data.py` / `seed_demo.py`
  bridge from P6a.
- OpenAPI regenerated to `contract/` and synced into `web/src/generated/`.

**Exit gate**, contract tests assert every route emits its schema; a request to a
removed route is a 404; `docker compose up` seeds a multi-train, multi-day
timetable; a thin system test searches a date, books a seat and gets a receipt.

---

## P6c: Traveller app · tier: UNIT + INTEGRATION + CONTRACT

The user-facing rebuild. Same hexagon, new screens. Built inward-out; every
screen is driven by a pure model that is unit-tested before the component exists.

**The flow** (one funnel, D26): **landing → search → trains → seats → passenger →
receipt**, with `back` legal from every step.

**The look** (D27): Rose Pine, **light mode only**, built out of Skeleton
utilities. Two lines in `app.css` pin it before any screen is written:
`:root { color-scheme: light }` after the Skeleton import, and a `dark` variant
redefined to a selector the app never emits, so neither the visitor's OS setting
nor a stray `dark:` utility can flip the palette. Reach for the Skeleton
primitive first, every time:

| Need | Skeleton primitive | Not this |
|---|---|---|
| Any panel, train row, receipt | `card` + `preset-tonal-*` / `preset-outlined-*` | a hand-rolled `rounded-xl border bg-…` stack |
| Buttons, the Reserve CTA, coach tabs | `btn`, `btn-group`, `preset-filled-primary-500` | custom padding/radius per button |
| Coach type, class, seat status pills | `badge`, `chip`, `badge-icon` | bespoke pill spans |
| Date, From/To, NIC, name | `input`, `select`, `label`, `input-group` | raw `<input>` with ad-hoc classes |
| Errors, "seat just taken", success | Skeleton alert/toast presets | the hand-rolled `Toast.svelte` from P6a |
| Loading a train list or seat map | `placeholder animate-pulse` | a spinner div |
| Hold countdown, seat-fill meter | `progress` | a manual bar |
| Section rules, legend separators | `hr`, `divider` | margin hacks |
| Icons | **lucide** via one `Icon` wrapper | hand-drawn SVG paths |

A hand-written component is allowed only where Skeleton has no equivalent (the
seat-map grid itself is the main one), and the reason goes in a comment above it.

**Deliverables**
- `view-core/` (unit): `flow.js` (the step reducer, including "seat taken → back
  to seats"), `trains.js` (search-result rows: time, duration, free counts,
  from-fare), `seatmap.js` **rewritten** to the layout model of D25 (rows of
  `left block · row number · right block`, exit-row separators, per-leg status
  per seat, coach list for the switcher), `receipt.js` (receipt view-model),
  `qr.js` (pure reference → QR matrix/SVG string), `time.js` (HH:MM + duration
  formatting).
- `ports/` + `adapters/`: `ApiClient` gains `searchTrains`, `confirm` returns a
  receipt, loses `unreserved` and `joinWaitlist`; **new `ReceiptExporter` port**
  with a real adapter (`window.print` for PDF, canvas → PNG download) and a
  recording fake, because printing is a browser capability and browser
  capabilities live behind ports.
- `ui/` (integration on the fake client):
  - `Header` / `Footer` (lucide icons, replacing the hand-rolled `Icon` paths).
  - `Landing`, short enough not to scroll: hero, one **Reserve** CTA, three
    value props, footer.
  - `JourneySearch`: Skeleton `input`/`select` for date and From/To, validated
    against the station list (no reversed or identical pairs, no date outside
    the window).
  - `TrainList`: one Skeleton `card` per train, number + name, depart → arrive,
    duration, class `chip`s, free-seat `badge`, from-fare, Select. Empty state is
    a `placeholder` that names the reason ("no trains run this route on
    Tuesdays") instead of showing nothing.
  - `CoachSwitcher` + `SeatMap`: the reference layout, one coach at a time,
    switched by a Skeleton `select` (or `btn-group` at two or three coaches);
    unreserved coaches shown greyed and unselectable (D23); live grey-out over
    SSE; click to select. The seat cells are the one deliberately hand-built
    grid, seat status still expressed in `preset-*` classes so the theme owns
    the colours.
  - `PassengerForm` + fare summary + one **Reserve & pay** action (the hold stays
    internal, D6), graceful **409** ("that seat was just taken") back to the map.
  - `Receipt`: reference, QR, train, date, leg + times, coach/seat, fare, and
    **Print / Download** through the exporter port.
- `app/` shell: header, footer, providers, env wiring, real-adapter injection.

**Exit gate**, every view-core module unit-tested (including the reducer's
back/conflict paths and the seat-map grid against a 3-3 layout with exit rows);
components tested on the fake `ApiClient`; the runtime schema-validation contract
test still holds the seam; dependency-cruiser passes (no `fetch`, `EventSource`,
`localStorage` or `window.print` outside `adapters/`); **a lint rule fails the
build on any `dark:` utility or `prefers-color-scheme` query in `web/` or
`admin/`** (D27), and the app renders identically with the OS set to dark.

---

## P6b: Admin counter app · tier: UNIT + INTEGRATION + CONTRACT

The ticket-counter app. A second frontend hexagon over the same backend and contract,
with two jobs (D21): **sell** unreserved tickets and **verify** any ticket at the gate.
Unreserved exists only here (D23). It inherits P6c's look wholesale (D27): the same
`app.css` with Rose Pine pinned to light, the same Skeleton-first table of primitives,
the same lucide `Icon` wrapper. A counter screen under fluorescent light is the *last*
place to introduce a second palette.

**Deliverables** (backend lands in P4b/P5b)
- `view-core/` (unit): `receipt` (shared with the traveller app's model), `sell` (the
  counter-flow reducer), `verify` (verdict → what the inspector should see, including the
  NIC to compare against the passenger's card).
- `ports/` + `adapters/`: reuse the generated `api-client` for the admin routes, fake
  first; the `ReceiptExporter` port for printing; a `Scanner` port for the QR camera with
  a keyboard-entry fallback and a scripted fake.
- `ui/` (integration on the fake client):
  - **Sell:** passenger NIC + name, train and leg pickers, cash taken → receipt showing
    the assigned seat *or* the standing prediction ("sit on seat 14 after Peradeniya"),
    printed.
  - **Verify:** scan a QR or type the reference → verdict banner (valid / not found /
    cancelled / expired / wrong day) with passenger NIC, train, leg and seat.
- `app/` admin shell, counter-key config.

**Exit gate**, view-core unit-tested; components tested on the fake `ApiClient`; a contract
test validates the admin responses against the OpenAPI schema; a sell flow produces a
receipt with a seat or a standing prediction, and verifying that receipt's reference
returns `VALID` with the matching NIC.

---

## P7: System / E2E · tier: SYSTEM

> **Revised.** No Playwright, no browser E2E suite, that scope was cut in favour of
> proving the same guarantees at the use-case/repository level against a real
> Postgres, which is what actually carries the correctness risk. The golden path
> (search → pick a train → pick a seat → pay → receipt with a QR) is already
> exercised end to end in P5b's contract/system tests and by hand via
> `docker compose up`.

**Deliverables**, all against a real Postgres (Testcontainers), not a fake:
**segment resale** (A→B and B→C on the *same seat* both succeed, the signature
journey — `test_segment_resale_adjacent_legs_on_the_same_seat_both_confirm` in
`test_real_pass.py`, reproduced headless by `make demo-resale`); **N browsers race
one seat** (one wins, N−1 get `OverlapError`/409 — `make demo-concurrency` and
`tests/integration/concurrency/`); a train that does not run on the chosen weekday
is absent from search results (`test_search_trains.py`); hold expiry frees the seat
(`test_repository.py`); **counter sells an unreserved ticket and then verifies its
reference** (the cross-app journey —
`test_a_counter_sale_verifies_the_same_way_as_an_app_booking` in
`test_verify_ticket.py`).

**Exit gate**, `make check` is green (all of the above run in its integration
tier); `make demo-resale` and `make demo-concurrency` each print their proof
headless against a throwaway Postgres.

---

## P8: Seed & config realism · one-command bring-up

Prove **nothing is hardcoded** (D11) and the clean-machine story holds.

**Delivered**, `config/timetable.json`: the real 11-station Colombo Fort–Badulla
route with km, three real service patterns (1005 Podi Menike and 1015 Udarata
Menike daily, 1045 Denuwara Menike Fri/Sat/Sun overnight), five coach layouts
(rows, columns, exit rows, reserved and unreserved, first/second/third class)
assembled per pattern, and fares/caps/velocity/hold-TTL/booking-window all env-driven
(`.env.example`). `tests/integration/test_seed_config.py` asserts coach/seat/station
counts **and the set of trains on a given weekday**
come from config (change config → results change, no code edit).

**Exit gate**, on a clean machine, `cp .env.example .env && docker compose up`
yields a usable, seeded app with a real timetable; the config-drives-counts test
is green.

---

## P9: Docs & polish

**Deliverables**, `README.md`: core design decisions + alternatives rejected
(from PLAN D1–D27), the sourced evidence + the transparent per-km derivation, the
concurrency-proof walkthrough, extra-credit write-ups, and the run instructions.
Architecture diagram; `make demo-*` scripts referenced. Repo made public.

**Exit gate**, a first-time reader can understand *why*, run it in two commands,
and watch the concurrency guarantee hold.
