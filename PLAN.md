# PLAN: Segment-Based Train Seat Booking System

The rebuild contract for the Colombo Fort–Badulla booking system. It binds the
generic [`FULLSTACK_ARCHITECTURE.md`](FULLSTACK_ARCHITECTURE.md) to this concrete
problem: what gets built, in what order, and the numbered decisions (D1–D27)
behind every non-obvious choice. Read the architecture for *why the shape*; read
this for *what and when*.

---

## 0. The thesis (why this project is more than a CRUD app)

Real, documented problems on this exact line, from research (sources at the
bottom):

- Reserved coaches **run visibly empty** while unreserved is overcrowded, the
  department has publicly denied losses over "images of empty compartments."
- Whole-journey pricing means a Fort→Kandy passenger **pays ~2× the unreserved
  fare** to cover a seat that then rides empty to Badulla.
- Reserved e-tickets **sold out in ~42 seconds** with an organized resale racket
  (one Colombo ticket resold for **LKR 40,000**; active **CID investigation**),
  until SLR responded in **Aug 2025** with named, **NIC/passport-verified,
  non-transferable** reserved tickets checked *at boarding*. Resale is now a
  partially-closed problem; the underlying **scarcity** (42-second sellouts) is
  untouched by an ID rule.

**The reframing that drives the design:** segment resale is an *anti-scarcity
mechanism*, not just a feature. Letting one physical seat serve multiple
non-overlapping legs raises effective reserved capacity, which directly attacks
the two problems the Aug-2025 NIC rule does **not** touch, (a) empty-coach waste
and (b) unfair short-leg pricing, and also relieves (c) the artificial scarcity
that fed the tout economy in the first place. Our anti-hoarding controls (named
passenger + NIC, seat caps, velocity limits) are deliberately **at parity with
SLR's live Aug-2025 policy**, table stakes, not the headline. **Capacity and
fair pricing are the story; touts are a downstream win.** That is the story the
README tells leadership.

---

## 1. Decisions (D1–D27)

| # | Decision | Why / alternatives rejected |
|---|---|---|
| **D1** | **Stack:** FastAPI + SQLAlchemy 2.0 + Postgres (backend), **Svelte** + Vite + **JavaScript** (frontend), Docker Compose. Tests: pytest + Hypothesis + Testcontainers + Playwright + Vitest. | Closest to the user's Research Hexagon (import-linter enforceable), strong Postgres story for concurrency. Plain JS (not TS) on the FE, contract safety comes from *runtime* schema validation against OpenAPI (D13), not the compiler. **Svelte over React:** the complexity and marks live in the backend; the frontend hexagon is framework-agnostic (view-core is plain JS, only `ui/` is framework-bound), so the choice is free, pick the one already fluent to avoid burning budget learning a framework. Rejected TS-full-stack (less aligned) and Go (more boilerplate). |
| **D2** | **Occupancy = half-open station intervals `[origin, destination)` + Postgres GiST `EXCLUDE` constraint.** Overlap is a *database invariant*, not app logic. | Adjacent legs `[A,B)` & `[B,C)` don't overlap → both book. Rejected `SELECT FOR UPDATE` (correctness in raceable app code) and `SERIALIZABLE`+retry (more moving parts, abort storms). The constraint is declarative and un-raceable. |
| **D3** | **Unify both coach types on one mechanism: an unreserved coach is a reserved coach with hidden, auto-assigned seats.** N non-overlapping intervals across N virtual seats = per-leg capacity, enforced by the *same* `EXCLUDE` constraint. Unreserved is **sold at the ticket counter only** (D23), the packing optimizer picks the hidden seat at payment time, or standing is issued (D20, D21). This puts the admin counter app in scope (revises D15). | One occupancy model, one correctness proof, one code path. The packing optimizer (D10) picks the virtual seat. Rejected a separate per-segment capacity-counter table (second concurrency mechanism to get right). |
| **D4** | **Fare = distance baseline + a demand/occupancy-aware `DynamicFare`, both behind a `FareStrategy` port.** `fare = rate_per_km · (km[dest] − km[origin]) · class_mult · demand_mult`. | Segment resale recovers the "empty leg," so reserved no longer needs the ~2× penalty, `DynamicFare` prices per-leg fairly. Directly answers leadership's revenue/fairness framing. Strategy seam keeps core pure. |
| **D5** | **Scheduling:** `ServicePattern` (recurring template) → dated `Trip` instances; a `Booking` attaches to a `Trip`. Availability is per-Trip. **Made concrete in D22** (days-of-week, several named trains per day, per-station times). | The honest "real product" model, the same seat on Aug 12 vs Aug 13 is independent. Rejected single-journey (too abstract) and dateless-templates (can't represent days). |
| **D6** | **Lifecycle:** `reserve → HOLD(TTL) → confirm(mock pay) → CONFIRMED → receipt (D24)`; `cancel/expire → segment reopens` and the freed leg is pushed to every watching client over SSE. | Hold prevents mid-checkout sniping; mock payment is a `PaymentGateway` port. Full lifecycle exercises concurrency at both hold and confirm. The hold is an internal step, the traveller sees one "Reserve & pay" action. |
| **D7** | **Real-time:** Server-Sent Events stream per Trip pushes availability deltas; optimistic UI with graceful 409 handling. | One-way is all availability needs; simpler than WebSockets, no extra infra. |
| **D8** | **Identity:** no accounts/login. A booking records passenger name + NIC/passport and returns a reference. **Named-passenger-per-seat** is a policy (must match on board). | Removes anonymous-resale value (anti-tout). This **mirrors SLR's live Aug-2025 rule**, named, NIC/passport-verified, non-transferable reserved tickets. Rejected full auth (budget away from core) and fully-anonymous (breaks named-passenger policy). |
| **D9** | **Anti-tout controls:** per-passenger seat caps + booking velocity limits (config-driven); `AbuseScorer` port (heuristic now, **ML-ready**); idempotency keys; hold TTL; named-passenger policy. | These are **at parity with SLR's Aug-2025 verified-ID policy**, table stakes, not our headline. Our net-new lever against the racket is removing the *scarcity* it feeds on, via segment resale (D2). `AbuseScorer` keeps an ML seam without committing to a model. |
| **D10** | **Seat-packing optimizer** (pure interval-partitioning, L0) used two ways: (1) at assignment time, pick the seat that best preserves long contiguous availability (max future sellable seat-km); (2) an **impact metric**, capacity/revenue unlocked vs rigid whole-journey booking. | Provably optimal (greedy on sorted intervals), property-tested, quantifies "revenue left on the table." Serves D3's virtual-seat assignment too. |
| **D11** | **Everything configurable:** number of coaches, seats/coach, coach class & type (reserved/unreserved), standing capacity/coach, stations + km positions, fare rates, caps/limits, hold TTL, all from config/seed, **nothing hardcoded**. | Explicit challenge requirement (department may add coaches / extend the route). |
| **D12** | **Hold expiry handled lazily inside the booking transaction** (expired holds for the target seat are retired before the new insert), plus a periodic sweeper for hygiene. | The partial `EXCLUDE ... WHERE status IN ('HELD','CONFIRMED')` can't reference `now()`; lazy retirement keeps correctness independent of the background job. |
| **D13** | **Contract seam:** FastAPI's OpenAPI is the source of truth. The FE is plain **JavaScript**, so drift is caught at **runtime**: a generated JS client + contract tests validate every response against the OpenAPI schema, fake and real client alike. | No hand-copied shapes. Without a compiler, *runtime* schema validation is what makes a FE/BE mismatch a red build, arguably a stronger guarantee than trusting generated types. |
| **D14** | **Enforcement:** import-linter (dependency rule + "use-cases never import a concrete adapter" + "frameworks out of L0/L1") + source-scan tests (no clock/rng/env/IO in inner layers) + a `guard` that plants a banned import and expects rejection. | Boundaries you can't run get crossed (architecture §5). |
| **D15** | **No LLM agent.** The admin counter app is now in scope (D21); it was de-scoped earlier. The AI/ML surface is the `AbuseScorer` seam; an agent could later be added as a pure composition-root entrypoint over existing use-cases. | Focus on the segment/concurrency core; an LLM agent is large for marginal payoff here. Counter settlement drives the unreserved flow, so its admin app earns its place. |
| **D16** | ~~Waitlist promotion = FIFO among compatible entries.~~ **WITHDRAWN.** No waitlist. A sold-out leg answers with the trains that *do* have room: another departure that day, another date, or a shorter leg on the same train. The `waitlist` table, port, use-cases, routes and UI are deleted. | A waitlist is a second queueing mechanism (its own table, port, promotion path, notification, UI, E2E journey) bolted beside the one that already exists, the hold queue. Segment resale (D2) is the real answer to scarcity: it *creates* the seats a waitlist would only ration. Cutting it removes ~6 files and a whole failure mode, and the search screen (D22) makes "no seats on this train" a useful answer instead of a dead end. |
| **D17** | **Payment is a mock `PaymentGateway` port**; fake supports success and a forced-decline path for tests. No real money, no secrets. | Meets "mock payment" without PCI scope. |
| **D18** | **Notifications via a `Notifier` port** (fake records; real logs / stub email) + an SSE toast on the client. | Confirmations and counter settlements need a channel; keep it swappable. |
| **D19** | **Migrations via Alembic**, including `CREATE EXTENSION btree_gist` and the `EXCLUDE` constraint. Seed via a config-driven seeder run by compose. | One-command bring-up; the constraint is schema, not app code. |
| **D20** | **Standing overflow for unreserved** (revises the old "cap at seat count, no standing" default). When no seat is free for the whole leg, issue a **STANDING** ticket, capped by config `standing_capacity` per coach, instead of "sold out", and predict the earliest station a seat frees for the rest of the journey: *"sit on seat X after station Y"*, printed on the counter receipt (D24). Standing pays the same per-leg unreserved fare. The prediction is computed once, at counter payment (D21); it is advice on the ticket, not a reservation, so no promotion queue exists. | Matches how unreserved really works (people stand; seats free as riders alight). Reuses the interval math + FIFO promotion with **no new mechanism**, the station/seat prediction is a pure `packing` sweep, property-testable like the rest. |
| **D21** | **Admin counter app (shared backend, separate frontend), two jobs: sell and verify.** **Sell:** the clerk enters the passenger's NIC + name, trip and leg, takes cash, and the system assigns a seat (packing) or standing (D20) and prints a receipt (D24). **Verify:** the inspector scans a receipt QR or types the reference and gets the booking back, passenger NIC, train, leg, coach/seat or standing, status, so the printed ticket can be checked against the ID it is named for. Verification serves **both** channels (reserved bought in the app, unreserved bought at the counter). Auth is a shared counter key for the demo, with staff login as the production upgrade. | Seat-at-payment matches real counters and stops unpaid intents from holding capacity. Verification is where SLR's named-ticket policy (D8) actually bites, an ID rule nobody can check is not a rule. One backend serves both apps; the admin frontend is a second hexagon over the same API and contract. |
| **D22** | **Timetable, made real: config `ServicePattern`s → materialized dated `Trip`s.** A pattern is config (D11): train number + name, route, `days_of_week`, per-station arrive/depart offsets from the origin departure, and a coach-layout reference. A seeder expands every pattern across a rolling `booking_window_days` into `trip` rows with a deterministic id (`{pattern_code}:{date}`), so re-seeding is idempotent. **Search becomes `(origin, destination, date) → trains`**: only patterns that run on that date's weekday, stop at both stations, and stop at the origin before the destination. Each result carries departure/arrival time for *that leg*, duration, free-seat count per class and a from-fare. **Up direction only** (Colombo Fort → Badulla); a return service would be a pattern whose station list is stored in travel order, which changes seed data and nothing else. | D5 promised dated instances but the build has one hardcoded trip, so "different trains on different days" is currently unrepresentable, and a date picker that changes nothing is a lie. Patterns in config keep D11 intact (a new train is config, not code). **Materializing** rather than computing trips on the fly keeps `trip` the single anchor the booking `EXCLUDE` constraint hangs off, one code path, no virtual-trip special case. Rejected: a `service_pattern` table (a second source of truth beside config, for data that is never queried on its own). |
| **D23** | **Unreserved leaves the public app entirely.** No `/unreserved` route, no unreserved mode in the traveller UI. The counter clerk creates *and* settles an unreserved sale in one transaction (`sell_unreserved`), so `PENDING` is an internal step, never a state a passenger walks around in. The traveller app shows unreserved coaches on the seat map as context only, greyed and unselectable. **Revises D3 and D21.** | An unpaid in-app "intent" that must still be paid for at a counter is worse than the walk-up it replaced: the passenger queues anyway, and the system carries a class of bookings that may never be paid. Real unreserved travel is cash at a window. This deletes a public endpoint, an abuse surface (free `PENDING` bookings are a denial-of-capacity lever), and a whole UI mode. |
| **D24** | **One receipt shape for both channels: reference code + QR.** On payment the passenger gets a receipt, human-readable reference (`SLR-7K3M-92`), a QR encoding that reference, passenger name + NIC, train number/name, date, from → to with times, coach + seat (or the D20 standing prediction), fare, issued-at. In-app for reserved, printed at the window for unreserved. Exportable from the app (print-to-PDF and PNG download) behind a frontend `ReceiptExporter` port. **Verification is an online lookup** by the admin app; the QR carries the reference and nothing else. **There is no public lookup-by-reference route**, `GET /bookings/{reference}` is removed from the public API and lives only behind the counter key. | One receipt means one contract shape, one view-model, one set of tests, and the inspector's screen looks the same whichever window the ticket came from. Online lookup makes the server the source of truth, so a forged QR fails for the only reason that matters, no such booking. Rejected an HMAC-signed offline token: a signing secret, a `Signer` port and key handling, bought only for scanners with no network. Removing the public lookup closes an enumeration hole, a guessed reference would otherwise return a stranger's NIC. Cost: close the tab, lose the receipt, accepted. |
| **D25** | **Seat-map geometry is config data carried on the contract.** A coach layout declares `rows`, a column pattern (`3-3`), and `exit_rows`; the trip response ships a `coaches[]` block with it, and `view-core/seatmap.js` turns seats + layout into rendered rows (left block · row number · right block) with exit-row separators. The UI renders that model and owns no geometry. | D11 says a coach's shape is config; the seat map is the one screen where violating that is invisible until a coach changes. Keeping geometry pure and on the contract means "add a coach with 2-2 seating" is a config edit with a unit test, not a component rewrite. |
| **D26** | **Traveller app = landing page + a linear booking wizard**, its step machine a pure reducer in `view-core` (`landing → search → trains → seats → passenger → receipt`), with **lucide** icons and no router library. | The flow is one funnel, not a set of addressable pages; a reducer is unit-testable at L0 where a router is not, and every step transition (including "seat taken, go back") becomes an assertion rather than a click-through. No deep links are needed now that there is no ticket-lookup screen (D24). |
| **D27** | **Skeleton first, and Rose Pine pinned to light.** Every visual primitive comes from Skeleton's utility layer (`card`, `btn`, `preset-*`, `badge`, `chip`, `input`/`select`, `table`, `divider`, `placeholder`, `progress`, `dialog`) before a single hand-written Tailwind block. A hand-rolled component is only justified when Skeleton has no equivalent, and the reason goes in a comment. **The app renders in light mode always:** `color-scheme: light` is pinned in `app.css` and the `dark` variant is redefined to a selector we never emit, so neither the visitor's OS setting nor a stray `dark:` utility can flip it. Rose Pine stays the theme; its light side (`--color-root-bg-light`, the Dawn cream) is the whole palette we ship. | Skeleton's presets are already theme-aware, accessible and consistent; hand-rolled equivalents drift from the theme the moment a token changes, and re-implementing a button is unpaid work that reviewers read as noise. Pinning light is a **product** choice: this is a public transport booking app used at a counter and in daylight, the design is tuned against one background, and a half-tested dark path is worse than none. It is also one fewer axis on every screenshot and E2E run. |

**Decisions to revisit** (sensible defaults set; flag if you disagree): classes
modeled as a config attribute on each coach with a fare multiplier; currency is
LKR; payment defaults to always-succeed with a test hook for decline; the
booking window is 30 days; seat-map colours are filled = free, pale = taken,
primary + tick = selected (we take the *layout* from the reference image, not its
colour semantics).

---

## 2. Domain model

```
Station        code, name, seq (order on line), km (from origin)
ServicePattern code, train_no, name, route_code, days_of_week, dep_time,
               stops[] (station seq + arrive/depart offset in minutes),
               coach_layout_ref                             (config only, D22)
Trip           id = "{pattern_code}:{service_date}", pattern_code, train_no, name,
               route_code, service_date, stations[], stops[], coaches[], seats[]
                                                            (materialized from a pattern)
CoachLayout    code, type (RESERVED|UNRESERVED), class, rows, columns ("3-3"),
               exit_rows[], standing_capacity (unreserved only)   (from config, D25)
Seat           id, coach, coach_type, class, number, row, column
               (unreserved seats are hidden virtuals, never selectable)
Passenger      name, nic_or_passport                        (no account)
Booking        id, trip_id, seat_id (null until seated), leg int4range '[)',
               status (PENDING|HELD|CONFIRMED|CANCELLED|EXPIRED|STANDING),
               passenger_id, reference, fare_cents, held_until, idempotency_key,
               created_at
```

`PENDING` now exists only inside the counter-sale transaction (D23), and there is
no waitlist entity (D16 withdrawn).

**The one invariant that guarantees correctness** (D2, D3):

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE booking ADD CONSTRAINT no_overlap
  EXCLUDE USING gist (
    trip_id  WITH =,
    seat_id  WITH =,
    leg      WITH &&            -- '&&' = ranges overlap
  ) WHERE (status IN ('HELD', 'CONFIRMED'));
```

Two concurrent transactions inserting overlapping legs on the same seat/trip:
exactly one commits, the other fails atomically with a serialization/exclusion
error the API maps to `409 Conflict`. Adjacent legs never overlap and both
succeed. Cancelled/expired rows leave the constraint's scope, so a freed segment
is immediately re-bookable. **This is the whole concurrency story**, and Phase 3
proves it with N concurrent requests.

`leg` uses integer station **sequence** positions (`[origin_seq, dest_seq)`);
`km` drives fares. Unreserved coaches simply have `is_visible=false` seats that
the optimizer auto-assigns (D3).

---

## 3. Layer map (bound to this project)

Per [`FULLSTACK_ARCHITECTURE.md`](FULLSTACK_ARCHITECTURE.md). Ports listed in §4.

```
backend/
  domain/     L0  station/leg interval + overlap math · timetable (which pattern runs
                  on a date, leg times/duration) · fare functions (distance, dynamic)
                  · interval-partitioning optimizer · booking state machine
                  · anti-tout policy predicates · abuse heuristic          → UNIT
  ports/      L1  BookingRepo/TripRepo/UnitOfWork · Clock · IdGen · ReferenceGen
                  · PaymentGateway · Notifier · AbuseScorer · FareStrategy
                  · AvailabilityPublisher · Config
  adapters/   L2  *.real (SQLAlchemy/pg, mock-pay, log-notify, heuristic-abuse)
                  + *.fake (in-memory, deterministic)                       → INTEGRATION
  usecases/   L3  search_trains(origin,dest,date) · leg_availability · quote_fare
                  · hold_seat · confirm_booking(→receipt) · cancel_booking
                  · sell_unreserved(counter) · verify_ticket · impact_metric → INTEGRATION (fakes)
  app/        L4  FastAPI, routes, DI wiring, config load, SSE stream,
                  idempotency middleware, error→HTTP mapping, migrations,
                  pattern→trip seeder                                        → SYSTEM
frontend/
  view-core/  L0  fare/leg/time formatting · availability + seat-map grid model
                  · booking-wizard step reducer · receipt view-model · QR encode → UNIT
  ports/      L1  ApiClient · AvailabilityStream(SSE) · Storage · ReceiptExporter
  adapters/   L2  api.real (from generated client) + api.fake · sse.real/fake
                  · exporter.real (print/download) + fake                    → INTEGRATION
  ui/         L3  landing · journey search · train list · coach switcher + seat map
                  · passenger form · receipt (code + QR + export)
                  · optimistic UI + 409 handling                             → INTEGRATION (fakes)
  app/        L4  app shell · header/footer · providers · env wiring          → SYSTEM
admin/        a second frontend hexagon (same layers) for the counter: sell unreserved · verify ticket
contract/     OpenAPI (from FastAPI) → generated JS client; contract tests validate both sides against the schema at runtime
```

---

## 4. Ports (the costly-world seam)

| Port | Real adapter | Fake adapter |
|---|---|---|
| `UnitOfWork` / `BookingRepository` | SQLAlchemy + Postgres | in-memory with the same overlap check |
| `Clock` | system clock | fixed/advanceable time |
| `IdGen` / `ReferenceGen` | uuid / short-code | deterministic sequence |
| `PaymentGateway` | mock provider | success + forced-decline |
| `Notifier` | log / email stub | records messages |
| `AbuseScorer` | heuristic (velocity, fan-out) | scripted scores (ML-ready seam) |
| `FareStrategy` | Distance, Dynamic | fixed fare |
| `AvailabilityPublisher` | SSE broker | records deltas |
| `Config` | file + env | in-code fixture |

Every port has **one conformance suite** run against **both** adapters (the fake
is executable documentation of the contract). Use-cases depend on ports only.

---

## 5. Build order (phases): red before green, each tier owns its layer

> Index only. Full per-phase deliverables, exit gates, and the test-first
> workflow live in [`PHASES.md`](PHASES.md), the living execution plan.

| Phase | Deliverable | Test tier / gate |
|---|---|---|
| **P0 Rails** | repo layout, docker-compose (pg+api+web+migrate), Makefile (`check/lint/arch/test:unit/int/e2e/guard`), import-linter config, lean GitHub Actions (`guard`+`check`), `.env.example`, OpenAPI→JS client gen. `guard` proves enforcement is live. | arch + `guard` green |
| **P1 Domain (L0)** | interval/overlap math (Hypothesis), fare functions (oracle tests), packing optimizer (optimality + property tests), booking state machine, anti-tout predicates, abuse heuristic. Zero I/O. | **UNIT**, every module property/example-tested |
| **P2 Ports + fakes (L1/L2)** | all ports defined; in-memory fakes; one conformance suite per port (vs fake now). | **INTEGRATION** (fakes) |
| **P3 Real adapters (L2)** | SQLAlchemy models + Alembic (`btree_gist`, `EXCLUDE`); real repo passes the same conformance suite; **concurrency-proof test** (N concurrent holds on one leg → exactly one wins); real pay/notify/abuse. | **INTEGRATION** (Testcontainers Postgres) |
| **P4 Use-cases (L3)** | search, availability, quote, hold (caps+velocity+abuse+idempotency), confirm (pay), cancel, book_unreserved, settle_at_counter, lookup_booking, optimizer-driven assign, impact metric. ✅ *superseded in part by P4b* | **INTEGRATION** (all-fake; concurrency semantics pinned) |
| **P5 Backend root (L4)** | FastAPI app, routes, DI, config, SSE stream, idempotency middleware, error→HTTP (409/422/409-hold), admin routes with shared-counter-key auth, OpenAPI contract. ✅ *superseded in part by P5b* | contract + thin **SYSTEM** |
| **P6a Frontend (first cut)** | view-core (unit) → ports + fake client → real client generated from OpenAPI, responses schema-validated + SSE → UI → app shell. ✅ *replaced by P6c* | **UNIT** + **INTEGRATION** (fakes) + contract (runtime schema) |
| **P4b Domain + use-case revision** | withdraw the waitlist (D16); `timetable` domain module (D22); `search_trains(origin,dest,date)` returning trains with times, free counts and from-fares; `sell_unreserved` (counter, one transaction, D23); `verify_ticket` (D21); `receipt` assembly (D24); seat-map geometry on trips (D25). | **UNIT** + **INTEGRATION** (fakes) |
| **P5b Contract + routes revision** | drop `/unreserved`, `/waitlist/*` and public `GET /bookings/{reference}`; `TripOut` gains train identity, stop times and `coaches[]`; `ReceiptOut`; admin `POST /admin/unreserved/sell` and `GET /admin/verify/{reference}`; pattern→trip seeder in compose; OpenAPI regenerated. | contract + thin **SYSTEM** |
| **P6c Traveller app** | landing (header/footer, hero, one **Reserve** CTA) → journey search (date + from/to) → train list for that date → coach switcher + **seat map** in the reference layout → passenger + pay → **receipt with code, QR and export**. lucide icons; wizard as a pure step reducer (D26). | **UNIT** + **INTEGRATION** (fakes) + contract |
| **P6b Admin counter app** | second frontend hexagon for the counter: **sell** an unreserved ticket (NIC + leg → cash → seat or standing → printed receipt) and **verify** any ticket by QR scan or reference. | **UNIT** + **INTEGRATION** (fakes) + contract |
| **P7 System / E2E** | Playwright over full compose: search a date → pick a train → book a seat → receipt with a QR; **two browsers race one seat** (one 409, handled); **segment resale** (A→B and B→C same seat both succeed); a train absent on a day it does not run; hold expiry; counter sells unreserved then verifies the reference. | **SYSTEM** |
| **P8 Seed & config** | real Colombo Fort–Badulla stations + km, several named service patterns with days-of-week and times, coach layouts (rows/columns/exit rows), 8 coaches (3 reserved/5 unreserved), classes, fares, limits, all config/seed. *The pattern seeder itself lands early, in P5b, because search is meaningless with one trip; P8 is realism plus the config-drives-counts proof.* | one-command bring-up verified |
| **P9 Polish & docs** | README (design decisions + alternatives + challenges + extra-credit write-ups + the anti-tout/impact narrative), diagrams, concurrency-proof walkthrough. | |

Extra-credit features are woven through, not bolted on: the optimizer lives in
P1+P4, anti-tout in P1+P4, the seat map in P6c, the concurrency proof in P3, CI in
P0, the timetable in P4b+P8.

---

## 6. Enforcement & one-command run (built for reviewers)

The guiding constraint: **a reviewer clones the repo and has the whole system,
running and testable, with two commands, on a clean machine with only Docker.**

```bash
cp .env.example .env          # no secrets to fill in; sane defaults work
docker compose up             # -> Postgres + migrations + seed + API + web, all wired
#   API  http://localhost:8000   (OpenAPI docs at /docs)
#   Web  http://localhost:5173   (seeded Colombo Fort–Badulla trips ready to book)
```

- **Everything is containerized**, including migrations and seed as compose
  init steps with healthchecks, so services start in the right order and the app
  is usable the moment `up` finishes, no manual DB setup, no "run this script
  first."
- **Run the tests just as easily**, one command, no local Python/Node needed:

  ```bash
  docker compose --profile test run --rm test   # unit + integration + arch, in a container
  docker compose --profile e2e  run --rm e2e    # Playwright system tests against the live stack
  ```

- **The headline demo is one command:** `make demo-concurrency` fires N
  simultaneous booking requests at a single seat/leg and prints "1 booked, N−1
  got 409", the reviewer *sees* the exclusion constraint hold the line.
- **Gate:** `make check = typecheck (mypy) + lint (ruff + ESLint) + import-linter
  + dependency-cruiser + unit + integration`; a lean GitHub Actions job runs
  `make guard` + `make check` on push/PR, and E2E runs on demand against compose
  (`make test-e2e`, wired into CI as a separate non-blocking job in P7). Nothing merges
  red. (No FE compiler now, the contract seam is held by *runtime* schema-validation
  contract tests, D13.)
- **`make guard`** plants `domain → sqlalchemy` and expects import-linter to
  reject it, proof the gate is alive.
- **No secrets committed:** every credential is an env var; `.env` is gitignored,
  `.env.example` is checked in with working local defaults.

---

## 7. Evidence: every added feature earns its place

Each feature beyond the bare core is tied to a documented problem and, where
possible, a number from a reliable source. Reliability tier is marked:
**[O]** official (railway.gov.lk administration reports), **[B]** reputable
business/news, **[F]** seat61 fares, **[D]** derived from O/F figures,
**[R]** single-source reporting (treat as indicative). Full links in §8.

| Feature | Problem it targets | Evidence (number) | Tier |
|---|---|---|---|
| **Per-leg + dynamic fare** (D4) | Short-leg passengers overpay under whole-journey pricing | Colombo→Kandy 2nd-class reserved **Rs 1,200** vs full Colombo→Badulla **Rs 2,000**, ~41% of the 292 km route for ~60% of the fare = **~45% more per km** | [D] from [F]+[O] |
| **Segment resale + optimizer impact metric** (D2/D10) | Reserved coaches ride empty → lost revenue | A Colombo→Kandy booking strands **171 km (59% of route)** as resellable seat-km; SLR operating loss **Rs 40.4 bn (2021)**, **~Rs 331 bn** accumulated over 10 yrs, the largest of any state enterprise; 2024 narrowed to a **Rs 122.4 mn** operating loss on **Rs 27.8 bn** revenue | [D]/[B]/[O] |
| **Anti-tout suite** (D9), *parity with live policy* | Scalper black market on reserved seats (Jan 2025 racket) | ~42-s sellouts; single ticket resold up to **LKR 40,000**; active **CID investigation**. SLR's own **Aug-2025** fix = named, **NIC-verified, non-transferable** tickets checked at boarding, we match it; segment resale (D2) attacks the underlying scarcity the ID rule leaves intact | [R]/[B]/[O] |
| **Search across the timetable** (D22) | Instant sellouts leave genuine travelers stuck; a sold-out train is not a sold-out day | 42-second sellouts on a network that carried **101,580,809 passengers in 2024** (109.9 mn in 2023); the answer to a full train is the next departure or a shorter leg, which is why the waitlist (D16) was withdrawn | [R]/[O] |
| **Named receipt + QR verification** (D21/D24) | An ID rule nobody can check at the gate is not a rule | SLR's **Aug-2025** policy requires NIC/passport-verified, non-transferable tickets checked *at boarding*; the counter app is the thing that does the checking | [B]/[O] |
| **Real-time SSE + robust conflict UX** (D7) | Unreliable official booking experience | Documented failures, "service not reachable", registration errors, public fraud suspicions | [R] |
| **Concurrency proof + CI** (D14) | Resale raises write-contention on each seat → double-booking risk | No external stat, an engineering guarantee, *proven* by the N-concurrent test yielding exactly one winner | |

The through-line for the write-up: **capacity + fair pricing are the core; touts,
scarcity, and revenue are downstream wins**, quantified, not asserted.

---

## 8. Sources (with reliability tier)

**[O] Official, Sri Lanka Railways / govt**
- SLR Administration Report 2024, Table 1.4: **101,580,809 passengers** and **5,999,574,084 passenger-km** in 2024 (vs 109,889,467 / 7,043,989,635 in 2023); revenue **Rs 27,842.05 mn**, operating loss **Rs 122.40 mn**, loss on recurrent expenditure **~Rs 11.5 bn**. (Figures read directly from the report PDF via `pdftotext`.) `railway.gov.lk/web/images/pdf/admin report - 2024 y.pdf`
- Reserved-seat fare revision & reservation rules, `railway.gov.lk/web/images/pdf/reservedseatsfairenglish1.pdf`; `railway.gov.lk` network overview (Main Line, 292 km).

**[B] Reputable business/news**
- SLR lost Rs 40.4 bn in 2021, EconomyNext.
- ~Rs 331 bn accumulated losses over 10 yrs (largest SOE), publicfinance.lk; Daily FT ("losses top Rs 10 b in 2020").
- Empty reserved compartments dispute, Daily Mirror, "Railways deny losses despite images of empty compartments circulating online."
- **Mandatory ID-verification for reserved tickets**, named, NIC/passport, non-transferable, verified *at boarding and ticket checks*; launched **Aug 2025** to stop black-market resale, Newswire (2025-08-11); corroborated by 2025/26 traveler guides (Ella Hype). *This is why anti-tout is framed as parity, not novelty.*

**[F] Fares, seat61**
- Colombo–Kandy 2nd reserved Rs 1,200 (3rd Rs 900); Colombo–Nanuoya/Ella/Badulla 2nd Rs 2,000 (3rd Rs 1,500, 1st Rs 3,000), seat61.com/SriLanka.htm.

**[R] Single-source / indicative reporting** (grounds the anti-tout & UX features)
- 42-second sellouts; LKR 40,000 resale; CID e-ticket-racket probe, Ceylon Today, The Sunday Times ("scenic train rides tainted by online scammers"), Daily Mirror, LNW.
- Official reservation-system UX complaints ("service not reachable", registration failures), Fact Crescendo, Google Play reviews.

**[D] Derived**, the ~45% per-km overpricing and the 171 km / 59% resellable-seat-km figures are computed transparently from [F] fares and [O] route distances; the derivation is shown in the README so a reviewer can check the arithmetic.
```



