# PHASES — Build Order

How the system gets built. Each phase **builds one ring of the
[architecture](ARCHITECTURE.md), test-first, owned by the test tier that ring is
assigned to.** Decisions behind the choices are D1–D19 in [`PLAN.md`](PLAN.md).

> **This is a living plan.** Nothing here is fixed. Decisions, phase boundaries,
> and deliverables can be changed, reordered, or dropped the moment a better
> requirement or design surfaces — **changeability is a core goal of this
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
5. **Assume a hostile, careless public — not a careful researcher.** This system
   is used by random everyday users, not by us. Every layer's tests must cover the
   dumb, the malformed, and the adversarial: legs that are empty / reversed / out
   of order / off the route, negative or fractional passenger counts, double-clicks
   and duplicate submits, holding an already-held or already-expired seat,
   confirming after expiry, cancelling twice, integer/money overflow, absurd
   quantities, unicode/oversized strings, missing or extra fields, and races where
   two users fight over one seat. **The happy path is the easy 10%; the edge cases
   are the test suite.** Invalid input must fail loud and safe (typed error → clean
   4xx), never corrupt state. Property tests (Hypothesis / fast-check) exist partly
   to *generate* the dumb input we wouldn't think to write by hand.

| Phase | Ring built | Test tier that owns it |
|---|---|---|
| P0 | (none — the enforcement + infra spine) | arch gate + `guard` |
| P1 | Backend **L0 domain** | **unit** |
| P2 | Backend **L1 ports** + **L2 fakes** | **integration** (fakes) |
| P3 | Backend **L2 real adapters** | **integration** (real Postgres) |
| P4 | Backend **L3 use-cases** | **integration** (fakes + thin real) |
| P5 | Backend **L4 composition root** | **contract** + thin **system** |
| P6 | Frontend **L0→L4** | **unit** + **integration** + **contract** |
| P7 | Whole system | **system** (E2E) |
| P8 | Seed & config realism | one-command bring-up |
| P9 | Docs & polish | — |

---

## P0 — Rails (the spine that makes everything else test-driven)

Builds no ring; installs the machinery every ring depends on. **This comes first
because test-drivenness and enforcement are infrastructure, not habits.**

**Deliverables**
- Repo tree per [ARCHITECTURE.md](ARCHITECTURE.md); empty `__init__.py` per layer.
- `pyproject.toml` (ruff, mypy, pytest markers: `unit`/`integration`/`concurrency`/`contract`/`arch`), `web/` Vite+**Svelte**+JS+Vitest+ESLint+dependency-cruiser.
- `.importlinter` with the four contracts; `tests/architecture/` source-scan + test-doctrine checks (they pass trivially on an empty tree and tighten as code lands).
- `docker-compose.yml`: `db` (Postgres, healthcheck), `migrate`, `seed`, `api`, `web`; profiles `test` and `e2e`. `.env.example` with working local defaults.
- `Makefile`: `check`, `lint`, `arch`, `test:unit|int|e2e`, `guard`, `demo-concurrency`, `demo-resale`.
- GitHub Actions running `make check` + E2E on push.

**Exit gate** — `make guard` plants `slr/domain/_guard.py: import sqlalchemy`,
import-linter **rejects it**, cleanup runs. `make check` is green on the empty
tree. `docker compose up` starts and healthchecks pass.

---

## P1 — Backend L0 domain (pure) · tier: UNIT

The correctness-critical core, built entirely test-first. No I/O, no framework,
no clock — the source scan enforces it.

**Deliverables** (each lands as failing unit tests first)
- `stations.py` — `Station`, `Leg` as half-open interval over station sequence; `overlaps`, `is_adjacent`, `contains`, `distance_km`. **Hypothesis property tests**: overlap is symmetric; adjacent legs never overlap; no-overlap ⇔ resellable.
- `fares.py` — `Money` (LKR minor units); `distance_fare`; `dynamic_fare(occupancy)`. **Oracle tests** against hand-computed fares (incl. the derived Kandy-leg example from PLAN §7).
- `packing.py` — interval-partition optimizer (min seats), best-seat selection (maximise future contiguous seat-km), `impact_seat_km`. **Property + optimality tests**: never assigns overlapping legs to one seat; result ≤ naive; matches greedy optimum.
- `booking_sm.py` — status transitions + guards. Tests: illegal transitions raise; expiry frees.
- `policy.py` — `within_seat_cap`, `within_velocity`, `named_passenger_ok` as pure predicates over (events, now). Tests cover boundaries.
- `abuse.py` — heuristic score (pure). `values.py`, `errors.py`.

**Exit gate** — every `domain/` module has a unit test (test-doctrine check
asserts it); property/oracle suites green; source scan confirms zero I/O/clock/rng.

---

## P2 — Backend L1 ports + L2 fakes · tier: INTEGRATION (fakes)

Define every seam to the costly world and its deterministic stand-in. **The fakes
and their conformance suites exist before any real adapter**, so L3/L4 are
testable without infrastructure.

**Deliverables**
- All port Protocols in `slr/ports/` (see [ARCHITECTURE.md](ARCHITECTURE.md#ports)).
- In-memory fakes for each; **`memory_repo.py` replicates the overlap invariant** (rejects overlapping active holds for the same trip+seat).
- **One conformance suite per port** in `tests/integration/ports/`, run against the fake now (and, unchanged, against the real adapter in P3). The booking-repo suite pins overlap/adjacency, hold expiry, and cancellation-frees-segment.

**Exit gate** — every port has a conformance suite (test-doctrine check);
all fakes pass; `usecases` can already be written against these interfaces.

---

## P3 — Backend L2 real adapters · tier: INTEGRATION (real Postgres)

Make the seams real. The proof of concurrency correctness lands here.

**Deliverables**
- SQLAlchemy 2.0 models + Alembic migrations, including `CREATE EXTENSION btree_gist` and the partial `EXCLUDE USING gist (trip_id =, seat_id =, leg &&) WHERE status IN ('HELD','CONFIRMED')`.
- `sqlalchemy_repo.py` — translates the DB `IntegrityError` → `OverlapError`; retires expired holds lazily inside the booking transaction (D12).
- Real `system_clock`, `uuid_ids`, `mock_payment`, `log_notifier`, `heuristic_abuse`, `distance_fare`/`dynamic_fare`, `sse_publisher`, `env_config`.
- **The same P2 conformance suites now run against the real adapters** via Testcontainers-Postgres.
- **Concurrency-proof test** (`tests/integration/concurrency/`): N simultaneous `add_hold` on one seat/leg → exactly one commits, N−1 raise `OverlapError`; adjacent legs both commit.

**Exit gate** — real adapters pass the *identical* conformance suites the fakes
passed; concurrency proof green; `make demo-concurrency` prints "1 booked, N−1 got 409".

---

## P4 — Backend L3 use-cases · tier: INTEGRATION (all-fake, thin real)

Orchestrate intents through ports only. Written and tested against **all-fake**
adapters (fast, deterministic), so concurrency/error semantics are pinned without
infrastructure; a thin real pass covers `hold`/`confirm`.

**Deliverables** — `search_trips`, `leg_availability`, `quote_fare`,
`hold_seat` (validate leg → caps/velocity/abuse → seat assignment via `packing`
for unreserved / requested seat for reserved → `add_hold` → idempotency),
`confirm_booking` (payment → transition), `cancel_booking` (→ `promote_waitlist`),
`join_waitlist`, `promote_waitlist` (FIFO among compatible — D16), `impact_report`.

**Exit gate** — every use-case has a fake-based test (test-doctrine check);
error paths (cap exceeded, overlap→409, payment declined, expired hold) covered;
`usecases` imports no adapter and no framework (import-linter).

---

## P5 — Backend L4 composition root · tier: CONTRACT + thin SYSTEM

Wire real adapters into use-cases and expose HTTP. **The only code no inner tier
exercises directly.**

**Deliverables** — FastAPI `main.py` + `wiring.py` (real adapters injected),
`config.py`, `schemas.py` (Pydantic = the **contract source**), `routes/`
(trips, availability, `bookings` hold→confirm→cancel, waitlist, **SSE** stream),
`middleware/idempotency.py`, `errors.py` (Overlap→409, Cap→429, Invalid→422),
OpenAPI emitted to `contract/`.

**Exit gate** — OpenAPI generated; contract tests assert routes emit the schema;
app boots in compose behind a healthcheck; a thin API-level system test books a seat end-to-end.

---

## P6 — Frontend hexagon · tier: UNIT + INTEGRATION + CONTRACT

Same layering, mirrored. Built inward-out: view-core → ports → fake client → real
client → UI → shell.

**Deliverables**
- `view-core/` (unit): `legs`, `availability` (which seats are free for a leg), `seatmap` (layout model), `fares` (format), `booking` (hold-flow reducer). Vitest.
- `ports/` + `adapters/`: `api-client.fake` first (drives component tests), then `api-client.real` (JS client generated from `contract/`, responses validated against the OpenAPI schema at runtime); `availability-stream.real` (`EventSource`) + fake; `storage.*`.
- `ui/` (integration on the fake client): `RoutePicker`, `DatePicker`, **`SeatMap`** (per-leg availability colouring, click-to-hold), `HoldTimer`, `ConfirmForm`, `WaitlistButton`; optimistic UI with graceful **409** handling; live grey-out via SSE.
- `app/` shell, router, providers, env, real-adapter injection.

**Exit gate** — view-core modules unit-tested; components tested on the fake
`ApiClient`; contract test validates the real client's responses against the
OpenAPI schema at runtime (no FE compiler — this is what holds the seam);
dependency-cruiser passes (no `fetch` outside `adapters/`).

---

## P7 — System / E2E · tier: SYSTEM

Full stack via `docker compose`, driven black-box. Small set, high value —
depth lives in P1–P6.

**Deliverables** (Playwright) — happy-path book; **segment resale** (A→B and B→C
on the *same seat* both succeed — the signature journey); **two browsers race one
seat** (one 409, handled gracefully); waitlist join → auto-promotion on cancel;
hold expiry frees the seat.

**Exit gate** — all journeys green in the CI `e2e` profile;
`make demo-resale` reproduces the resale journey headless.

---

## P8 — Seed & config realism · one-command bring-up

Prove **nothing is hardcoded** (D11) and the clean-machine story holds.

**Deliverables** — config-driven seed of real Colombo Fort–Badulla stations + km,
8 coaches (3 reserved / 5 unreserved) with classes, fare rates, caps, velocity
limits, hold TTL. A test asserts coach/seat/station counts come from config
(change config → counts change, no code edit).

**Exit gate** — on a clean machine, `cp .env.example .env && docker compose up`
yields a usable, seeded app; the config-drives-counts test is green.

---

## P9 — Docs & polish

**Deliverables** — `README.md`: core design decisions + alternatives rejected
(from PLAN D1–D19), the sourced evidence + the transparent per-km derivation, the
concurrency-proof walkthrough, extra-credit write-ups, and the run instructions.
Architecture diagram; `make demo-*` scripts referenced. Repo made public.

**Exit gate** — a first-time reader can understand *why*, run it in two commands,
and watch the concurrency guarantee hold.
