# Segment-Based Train Seat Booking — Colombo Fort–Badulla

One reserved seat, sold and resold for multiple non-overlapping legs of the
same journey (Colombo→Kandy, then Kandy→Badulla on the *same seat*), each
passenger charged only for distance travelled.

Three apps, one backend: **traveller app** (search/seat map/book/receipt),
**admin counter app** (sell unreserved for cash, verify tickets), **FastAPI**
backend owning the concurrency invariant.

Full reasoning: [`PLAN.md`](PLAN.md) (decisions D1–D27 + sourced evidence),
[`ARCHITECTURE.md`](ARCHITECTURE.md) (layering/enforcement).

## Reviewer map

| Want to see... | Look at |
|---|---|
| Concurrency guarantee | [below](#core-idea-occupancy-as-a-database-invariant), `backend/slr/app/migrations/` |
| Concurrency proof | `make demo-concurrency` |
| Segment resale working | `make demo-resale` |
| Fare + seat-packing math | `backend/slr/domain/fares.py`, `packing.py` |
| Design decisions + evidence | `PLAN.md` §1 (D1–D27), §7–8 |

## Run it

```bash
cp .env.example .env
docker compose up          # builds on first run, use --build after pulling new code
```

- Traveller app — http://localhost:5173
- Admin app — http://localhost:5174
- API — http://localhost:8000 (`/docs` for OpenAPI)

`db → migrate → seed → api → web/admin`, wired with healthchecks, so the stack
is usable the moment `up` finishes. Stop with `docker compose down` (`-v` to
drop the DB).


## Test it

```bash
docker compose --profile test run --rm test   # unit + integration + arch, no local install
make check                                    # same, locally: lint+arch+types+unit+integration
make guard                                    # proves the enforcement gate is alive
make demo-concurrency                         # N holds race one seat/leg → "1 booked, N−1 got 409"
make demo-resale                              # A→B then B→C on one seat, real Postgres → both succeed
```

CI runs `guard` + `check` on every push (lean, one job). E2E (Playwright) runs
on demand against compose rather than blocking CI.

Tests are tiered, not feature-grouped: `tests/unit/` (pure domain, Hypothesis +
oracles), `tests/integration/{ports,usecases,concurrency,contract}/` (real+fake
conformance, use-case orchestration, the N-concurrent proof, OpenAPI
conformance), `tests/architecture/` (import-linter source scan + "every
port/use-case/domain module has a test"). `web/`+`admin/` mirror this with
Vitest + dependency-cruiser.

## Core idea: occupancy as a database invariant

A seat's occupancy is a set of half-open intervals `[origin, destination)`.
`[FORT,KDY)` and `[KDY,BAD)` share an endpoint but don't overlap, so both can
be sold on one seat. This is enforced by Postgres, not app code:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE booking ADD CONSTRAINT no_overlap
  EXCLUDE USING gist (trip_id WITH =, seat_id WITH =, leg WITH &&)
  WHERE (status IN ('HELD', 'CONFIRMED'));
```

Two concurrent holds on overlapping legs of one seat: exactly one commits, the
other gets an exclusion violation → API maps it to `409`. No `SELECT FOR
UPDATE`, no retry loop, and no race window to get wrong: the guarantee is
declarative and instance-count-independent. Cancel/expiry removes the row from
`HELD`/`CONFIRMED`, so a freed leg is instantly rebookable.

**Rejected:** row locking (correctness lives in raceable app code, plus lock
ordering across legs), and `SERIALIZABLE`+retry (abort storms under
contention). Unreserved coaches reuse this same mechanism through hidden
auto-assigned virtual seats, giving one occupancy model and one concurrency
proof instead of two.

**Fares:** `rate_per_km × distance × class_mult × demand_mult`, pure function,
oracle-tested, swappable via a `FareStrategy` port.

**Seat assignment:** a pure interval-partitioning optimizer
(`packing.py`) picks the seat that preserves the most future contiguous
seat-km, and is property-tested for optimality. The same algorithm produces
the "seat-km left on the table" impact metric behind the revenue argument in
`PLAN.md`.

## Configurable by design

Coaches, seats/coach, classes, stations, and fares are config + seed data
(`config/timetable.json`), not hardcoded. Adding a station, coach, or train
is a config edit plus a reseed, with no code change required. Policy (hold TTL, seat caps,
velocity limits, currency, fare rate) is `.env`-driven.

## Extra credit implemented

- **Seat map** — coach layout (rows/seating/exit rows) is config data on the
  contract, and `view-core/seatmap.js` renders it per-leg availability.
  Geometry changes stay a config edit, not a component rewrite.
- **Admin counter app** — sell unreserved for cash (auto seat/standing via the
  packing optimizer) + verify any ticket by reference/QR. Sale+settlement is
  one transaction, no walk-away-able `PENDING` state.
- **Standing tickets** — sold-out unreserved issues a capped standing ticket
  instead of refusing, with a predicted "seat free after station Y" reusing
  the same interval sweep.
- **Named receipt + QR** — one receipt shape for both channels, reference
  plus QR, exportable as PDF/PNG. Verification is an online lookup only, and
  deliberately has **no public lookup-by-reference route** (would let anyone
  enumerate a stranger's name/NIC). An HMAC offline token was considered and
  rejected.
- **Anti-tout controls** — named passenger+NIC, seat caps, velocity limits,
  idempotency keys, pluggable `AbuseScorer` (heuristic now, ML-ready). Built
  at parity with SLR's real Aug-2025 policy rather than as the headline
  feature, since segment resale is the actual novel lever that relieves the
  scarcity the ID rule doesn't touch. Sourcing is in `PLAN.md` §7–8.
- **Live availability (SSE)** — per-trip push so a seat someone else just took
  greys out live, and optimistic UI handles a lost-race `409` gracefully.
- **Timetable search over a waitlist** — a sold-out train surfaces the next
  departure/shorter leg instead of a dead end. A waitlist was designed then
  explicitly withdrawn (`PLAN.md` D16): it's a second queueing mechanism for a
  problem resale already solves better.
- **Enforced hexagonal architecture** — both backend and both frontends split
  into pure-core/ports/adapters/orchestration/composition-root, checked by
  import-linter + dependency-cruiser. `make guard` proves the gate is live by
  planting a banned import and asserting rejection. This keeps the one
  correctness-critical rule (the overlap invariant) pure, property-tested, and
  small-blast-radius.

## Challenges

- **Concurrency without a second locking mechanism** — an earlier draft used a
  per-segment counter table, which could disagree with a lock under a race.
  Collapsing reserved+unreserved onto one interval model removed that risk.
- **Hold expiry vs. the `EXCLUDE` constraint** — a partial index can't
  reference `now()`, so expired holds are retired lazily inside the next
  transaction on that seat, with a sweeper for hygiene only.
- **Contract safety without a TS compiler** (JS frontend by design) — a
  generated JS client + contract tests validate every response against the
  live OpenAPI schema at runtime, on both fake and real clients.

## Layout

```
backend/slr/   domain (pure) → ports → adapters (real+fake) → usecases → app (FastAPI)
web/           traveller app, same hexagon in JS/Svelte
admin/         counter app (sell/verify), same hexagon, same backend
contract/      OpenAPI, source of truth both frontends validate against
config/        route, coach layouts, service patterns
tests/         unit / integration (ports, usecases, concurrency, contract) / architecture
scripts/       demo_concurrency.py, demo_resale.py, dev_server.py, emit_openapi.py
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full map and cookbook of
where each kind of change belongs.
