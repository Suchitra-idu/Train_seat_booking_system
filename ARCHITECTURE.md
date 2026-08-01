# Architecture: Segment Booking System

This tree implements **the Fullstack Hexagon**, the generic specification lives
in [`FULLSTACK_ARCHITECTURE.md`](FULLSTACK_ARCHITECTURE.md). Read that for *why
the shape*. This file is the map: where things go, and what stops them going
anywhere else. The decisions (D1–D21) behind every deviation are in
[`PLAN.md`](PLAN.md); the build order and per-phase deliverables are in
[`PHASES.md`](PHASES.md).

Two goals govern every rule: **simplicity** (one obvious home per change) and
**changeability** (rewrite any one part in isolation, prove it against its
contract). The three test tiers are the mechanism, not an afterthought.

---

## The two hexagons

A backend hexagon and a frontend hexagon, meeting at one shared OpenAPI contract. Imports
point strictly inward (toward the pure, cheap, deterministic core). An inner
layer never knows an outer layer exists.

```
   BACKEND  (Python pkg `slr/`)                    FRONTEND  (`web/src/`)
   L4 app/        FastAPI, wiring, migrations       L4 app/        entry, routes, stores
   L3 usecases/   one intent per file, ports only   L3 ui/         .svelte components, stores (ports only)
   L2 adapters/   real + fake, side by side         L2 adapters/   api.real + api.fake, sse.*
   L1 ports/      interfaces to the costly world    L1 ports/      ApiClient, Stream, Storage, Clock
   L0 domain/     pure rules & math                 L0 view-core/  pure view-models & formatters
                         │                                  │
                         └──────  contract/ (OpenAPI → generated JS client)  ──────┘
```

### Backend layers

| Layer | Package | May import | Tested by |
|---|---|---|---|
| L0 | `slr/domain/` | stdlib only | **unit**, property tests (Hypothesis) + reference oracles |
| L1 | `slr/ports/` | `slr/domain` | conformance suites (defined here, run in L2) |
| L2 | `slr/adapters/` | `slr/domain`, `slr/ports`, any framework | **integration**, the port's conformance suite, run against **real *and* fake** |
| L3 | `slr/usecases/` | `slr/domain`, `slr/ports` (**interfaces only, never `slr/adapters`**) | **integration**, orchestration on all-fake adapters |
| L4 | `slr/app/` | everything inward | **system**, API black-box against `docker compose` |

### Frontend layers

| Layer | Dir | May import | Tested by |
|---|---|---|---|
| L0 | `web/src/view-core/` | stdlib/JS only | **unit** (Vitest) |
| L1 | `web/src/ports/` | `view-core` | interface shapes |
| L2 | `web/src/adapters/` | `view-core`, `ports`, browser APIs | **integration**, component tests vs fake; contract test real client vs OpenAPI |
| L3 | `web/src/ui/` | `view-core`, `ports` (**never `fetch`/`EventSource`**) | **integration**, components on the fake `ApiClient` |
| L4 | `web/src/app/` | everything inward | **system**, Playwright |

---

## The one invariant, and how the layers hold it

Correctness under concurrent booking is a **database invariant**, not application
logic (PLAN D2). It lives in exactly one migration and is honoured identically by
the real and fake repositories:

```
domain/stations.py   Leg.overlaps(other), pure half-open interval math      [L0, unit-tested]
ports/repository.py  BookingRepository.add_hold(...) raises OverlapError       [L1, contract]
adapters/sqlalchemy_repo.py   relies on the GiST EXCLUDE constraint;           [L2, real]
                              translates the DB IntegrityError → OverlapError
adapters/memory_repo.py       replicates the same overlap check in memory      [L2, fake]
app/migrations/*_exclude.py   CREATE EXTENSION btree_gist; EXCLUDE (…&&)        [L4, schema]
```

**The fake repo rejecting overlaps exactly as the real one does is not optional,
it is what makes the fast, infra-free inner tests trustworthy.** One conformance
suite (`tests/integration/ports/test_booking_repo.py`) runs against both and
asserts identical overlap/adjacency behaviour. The concurrency-proof test
(`tests/integration/concurrency/`) fires N simultaneous holds at the real adapter
and asserts exactly one wins.

---

## Ports (the costly-world seam)

Every port is a Protocol in `slr/ports/` with **one conformance suite** and a
**real + fake** adapter pair in `slr/adapters/`.

| Port | Real adapter | Fake adapter |
|---|---|---|
| `UnitOfWork` + `BookingRepository`/`TripRepository`/`WaitlistRepository` | `sqlalchemy_repo.py` (Postgres) | `memory_repo.py` (replicates the invariant) |
| `Clock` | `system_clock.py` | `fake_clock.py` (advanceable) |
| `IdGen` / `ReferenceGen` | `uuid_ids.py` | `seq_ids.py` (deterministic) |
| `PaymentGateway` | `mock_payment.py` | `fake_payment.py` (success + forced-decline) |
| `Notifier` | `log_notifier.py` | `memory_notifier.py` (records) |
| `AbuseScorer` | `heuristic_abuse.py` (**ML-ready seam**) | `scripted_abuse.py` |
| `FareStrategy` | `distance_fare.py`, `dynamic_fare.py` (selected by config) | `fixed_fare.py` |
| `AvailabilityPublisher` | `sse_publisher.py` | `memory_publisher.py` |
| `Config` | `env_config.py` (file + env) | `fixture_config.py` |

Two fare strategies are two adapters behind one port, selected by config, **not**
a registry. A registry earns its keep at the third variant (spec §8: "two ifs beat
a registry"); we have two.

---

## Enforcement: boundaries you cannot run get crossed

`make check` is the gate: `typecheck + ruff + import-linter + unit + integration`
(system runs on demand against compose via `make test-e2e`). Nothing merges red.

**`.importlinter`**, four contracts:

| Contract | What it stops |
|---|---|
| `layers` | order `slr.app > slr.adapters > slr.usecases > slr.ports > slr.domain`; forbids every outward import, including **`usecases → adapters`** (adapters sit *above* usecases, so a use-case cannot reach a concrete adapter) and anything importing `slr.app` |
| `domain-and-ports-are-pure` | `sqlalchemy`, `fastapi`, `alembic`, `httpx`, `pydantic` reaching `slr.domain` or `slr.ports` |
| `usecases-stay-framework-free` | frameworks in `slr.usecases`, costly deps arrive through a port, never directly |
| `adapters-dont-orchestrate` | `slr.adapters → slr.usecases` (adapters implement ports; they don't drive intents) |

**`tests/architecture/`**, what import-linter can't express:
- `test_domain_is_pure.py`, source scan banning, in `domain/` and `ports/`:
  `datetime.now`/`time.time` (clock), `random`/`secrets` (rng), `os.environ`
  (env), `open(`/filesystem, and any network call. These come through a port.
  (Comments and string literals excluded, naming an idiom in a docstring is not a
  violation.)
- `test_test_doctrine.py`, structural: **every port has a conformance suite,
  every use-case has a fake-based test, every `domain/` module has a unit test.**
  Missing test scaffolding fails the build like missing code.

**Frontend** mirrors this with `dependency-cruiser`: `ui → adapters` and
`view-core → (svelte|fetch|EventSource)` are errors; a source rule bans `fetch`/
`EventSource`/`localStorage` outside `adapters/`.

**`make guard`** proves the gate is alive: it plants `import sqlalchemy` in
`slr/domain/_guard.py`, expects import-linter to reject it, and cleans up.

---

## Where things go

```
<repo root>/
  FULLSTACK_ARCHITECTURE.md  generic spec (the why)
  ARCHITECTURE.md            this file (the map)
  PLAN.md                    decisions D1–D21 + sourced evidence + run
  PHASES.md                  build order + per-phase deliverables & gates
  docker-compose.yml         pg + migrate + seed + api + web (+ test / e2e profiles)
  Makefile                   check · lint · arch · test:{unit,int,e2e} · guard · demo-*
  .importlinter · .env.example

  contract/                  OpenAPI (emitted from FastAPI) → generated JS client (validated at runtime in tests)

  backend/  (pkg `slr/`)
    domain/     stations.py (Station, Leg, overlap/adjacency, distance)
                fares.py (Money, distance & dynamic fare, pure)
                packing.py (interval-partition optimizer, best-seat, impact seat-km)
                booking_sm.py (HOLD→CONFIRMED→CANCELLED/EXPIRED transitions)
                policy.py (caps, velocity, named-passenger predicates)
                abuse.py (heuristic score, pure)
                values.py · errors.py
    ports/      repository.py · clock.py · ids.py · payment.py · notifier.py
                abuse.py · fares.py · availability.py · config.py
    adapters/   sqlalchemy_repo.py / memory_repo.py · system_clock.py / fake_clock.py
                uuid_ids.py / seq_ids.py · mock_payment.py / fake_payment.py
                log_notifier.py / memory_notifier.py · heuristic_abuse.py / scripted_abuse.py
                distance_fare.py · dynamic_fare.py / fixed_fare.py
                sse_publisher.py / memory_publisher.py · env_config.py / fixture_config.py
    usecases/   search_trips.py · leg_availability.py · quote_fare.py · hold_seat.py
                confirm_booking.py · cancel_booking.py · join_waitlist.py
                promote_waitlist.py · impact_report.py
    app/        main.py · wiring.py · config.py · schemas.py (contract source)
                routes/ (trips, availability, bookings, waitlist, sse)
                middleware/idempotency.py · errors.py (domain→HTTP) · seed.py
                migrations/ (Alembic; btree_gist + EXCLUDE)

  frontend/ (`web/src/`)
    view-core/  legs.js · availability.js · seatmap.js · fares.js · booking.js
    ports/      api-client.js · availability-stream.js · storage.js · clock.js
    adapters/   api-client.real.js / api-client.fake.js
                availability-stream.real.js / .fake.js · storage.real.js / .fake.js
    ui/         RoutePicker · DatePicker · SeatMap · SeatCell · HoldTimer   (.svelte)
                ConfirmForm · WaitlistButton · stores (availability, hold)
    app/        main.js · App.svelte · routes · stores · env

  tests/  (backend)
    unit/         mirrors domain/
    integration/  ports/ (conformance, real+fake) · usecases/ (fakes)
                  concurrency/ (N-concurrent proof) · contract/ (OpenAPI)
    architecture/ source-scan + test-doctrine
  e2e/            Playwright system journeys
```

---

## The cookbook: to do X, edit only Y

| Task | Do this | Edit nothing else |
|---|---|---|
| Extend the route / add a station | config + seed (station name, seq, km) | availability & fares recompute; no code |
| Add a coach / change seats-per-coach | config (coach type, class, seat_count) | no code, D11 |
| Change a fare formula | `domain/fares.py` + its unit test | not the DB, not the API |
| Add a fare strategy | new adapter of `FareStrategy` + conformance + config to select | core untouched |
| Change hold TTL / seat caps / velocity limits | config data | never a rule |
| Add an anti-tout rule | `domain/policy.py` predicate + unit test; `hold_seat` calls it | one place |
| Swap the database | new `*_repo.py` passing the existing conformance suite | zero domain/use-case change |
| Add an external dep (SMS, real payments) | new port + real & fake adapters + conformance | use-cases call the port |
| Add an API endpoint | `app/schemas.py` (contract) → a `usecases/` intent → a route | domain untouched unless the rule is new |
| Upgrade abuse detection to ML | new `AbuseScorer` adapter passing conformance | nothing in domain/usecases |
| Change the seat map's look | `view-core/seatmap.js` model + `ui/SeatMap` | no `fetch` in components |

If a task makes you edit an inner layer to change something outer, or spread one
change across three layers, **stop. You are fighting the architecture.** That
friction is a design signal (spec §10).
