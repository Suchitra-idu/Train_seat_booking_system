# The Fullstack Hexagon

A reusable architecture for **any** fullstack application, designed so that an
LLM (or a human moving fast) can change it without breaking it. It is the
web/SE sibling of the Research Hexagon: same dependency rule, same ports with
real-and-fake adapters, same machine-enforced boundaries — retargeted from
"experiments over costly compute" to "features over costly I/O."

Two goals govern every rule below. When a rule and a goal disagree, the goal wins.

1. **Simplicity** — one obvious home for every kind of change; the smallest
   thing that could possibly work; nothing clever the tests don't force.
2. **Changeability** — you can rewrite any one part in isolation, prove it still
   honours its contract, and know the blast radius before you start.

Everything here — the layers, the test tiers, the enforcement — exists to serve
those two. The three test tiers are not a quality afterthought; they are the
*mechanism* by which an LLM can change this system safely. That is the thesis of
this document.

---

## 1. The one idea: dependencies point toward cheapness

Sort every line of code you will ever write onto a single gradient:

```
        CHEAP                                                 COSTLY
   pure · fast · deterministic  ───────────►  impure · slow · nondeterministic
   no I/O · no framework · no clock            DB · network · disk · time · UI
   trivially testable                          testable only against real infra
```

**The Dependency Rule: imports may only point toward the cheap end.** An inner
(cheaper) module never knows an outer (costlier) module exists. Business rules
never import a database; a formatter never imports React; the domain never reads
the clock.

This single rule buys both goals at once:

- **Simplicity** — where a thing goes is decided by what it *costs*, not by
  taste. Pure rule → inner. Talks to Postgres → outer. No debate.
- **Changeability** — you can swap anything costly (Postgres → MySQL, REST →
  gRPC, React → Svelte) without touching anything cheap, because the cheap side
  literally cannot reference it.

Every other rule in this document is a way to *enforce* or *exploit* this one.

---

## 2. The layers

A fullstack app is **two hexagons meeting at a contract.** The backend and the
frontend each obey the Dependency Rule internally; they meet only at a typed
API contract that neither owns alone.

```
  ┌───────────────── BACKEND hexagon ─────────────────┐        ┌───────────────── FRONTEND hexagon ────────────────┐
  │                                                    │        │                                                    │
  │  L4 Composition root  (http server, DI, config)   │        │  L4 Composition root  (app shell, router, env)    │
  │   ┌────────────────────────────────────────────┐  │        │   ┌────────────────────────────────────────────┐  │
  │   │ L3 Use-cases   (orchestration, via ports)   │  │        │   │ L3 UI shell   (components, hooks, state)    │  │
  │   │   ┌──────────────────────────────────────┐  │  │        │   │   ┌──────────────────────────────────────┐  │  │
  │   │   │ L2 Adapters  (real + fake, per port) │  │  │        │   │   │ L2 Adapters  (real client + fake)    │  │  │
  │   │   │   ┌──────────────────────────────┐   │  │  │        │   │   │   ┌──────────────────────────────┐   │  │  │
  │   │   │   │ L1 Ports  (interfaces)       │   │  │  │        │   │   │   │ L1 Ports  (interfaces)       │   │  │  │
  │   │   │   │   ┌──────────────────────┐   │   │  │  │        │   │   │   │   ┌──────────────────────┐   │   │  │  │
  │   │   │   │   │ L0 Domain (pure)     │   │   │  │  │        │   │   │   │   │ L0 View-core (pure)  │   │   │  │  │
  │   │   │   │   └──────────────────────┘   │   │  │  │        │   │   │   │   └──────────────────────┘   │   │  │  │
  │   │   │   └──────────────────────────────┘   │  │  │        │   │   │   └──────────────────────────────┘   │  │  │
  │   │   └──────────────────────────────────────┘  │  │        │   │   └──────────────────────────────────────┘  │  │
  │   └────────────────────────────────────────────┘  │        │   └────────────────────────────────────────────┘  │
  └───────────────────────────┬────────────────────────┘        └────────────────────────┬───────────────────────┘
                              │                                                          │
                              └──────────────►  CONTRACT  (typed API schema)  ◄──────────┘
                                     the seam both sides conform to, neither side owns
```

Five layers per side. **L0–L1 are mandatory and tiny. An optional L1.5
(Extensions) is described in §8 — use it only when you have genuine pluggable
variation.** Do not add layers a project has no need for; simplicity first.

### Backend layers

| Layer | Holds | May import | Must NOT contain |
|---|---|---|---|
| **L0 Domain** | Entities, value objects, business rules, calculations, invariants. Pure functions and data. | stdlib / language only | I/O, framework, ORM, clock, randomness, env, network |
| **L1 Ports** | Interfaces to everything costly: `Repository`, `Clock`, `Rng`, `IdGen`, `Mailer`, `Queue`, `PaymentGateway`. Interface + domain types only. | L0 | any implementation |
| **L2 Adapters** | One **real** and one **fake** implementation per port, side by side. Real = the driver (SQL, HTTP, SMTP). Fake = in-memory, deterministic. | L0, L1, any framework | business rules (those belong in L0) |
| **L3 Use-cases** | Application orchestration: "book a seat", "cancel order". One transaction / one intent each. Depends on **ports only — never a concrete adapter.** | L0, L1 (interfaces only) | direct DB/HTTP/framework calls |
| **L4 Composition root** | The HTTP framework, route handlers, dependency wiring, config/secrets loading, migrations, the process entrypoint. Wires real adapters into use-cases. | everything inward | business rules or orchestration (those are L3) |

### Frontend layers (the mirror)

| Layer | Holds | May import | Must NOT contain |
|---|---|---|---|
| **L0 View-core** | Pure view-models, formatters, validators, reducers, derived-state calculators. Given data, returns data. | stdlib / language only | React/DOM, `fetch`, `window`, timers, storage |
| **L1 Ports** | Interfaces to the browser's costly world: `ApiClient`, `Storage`, `Clock`, `Router`, `Analytics`. | L0 | any implementation |
| **L2 Adapters** | Real `fetch`/websocket client + **fake in-memory client**; real `localStorage` + fake map. | L0, L1, framework | view logic (that is L0) |
| **L3 UI shell** | Components, hooks, state management. Renders view-core output; calls ports for data. **Ports only — never `fetch` directly.** | L0, L1 (interfaces only) | direct network/storage calls |
| **L4 Composition root** | App entry, router setup, providers, env wiring, real-adapter injection. | everything inward | view logic or data logic |

### The contract (the seam)

A single typed schema — OpenAPI, a shared-types package, tRPC, GraphQL SDL,
protobuf — that describes every request and response. It is **generated or
shared, never hand-copied on two sides.** The backend's real adapter (its route
layer) proves it *produces* the contract; the frontend's real adapter (its API
client) proves it *consumes* the contract. Contract tests on both sides (§4)
make drift a red build, not a production incident.

---

## 3. Why this is *LLM-friendly*: change has one home

An LLM edits well when the task decomposes into: (a) find the one place, (b) get
a fast red→green signal, (c) be unable to reach sideways for a shortcut. This
architecture is built to give all three.

- **One home per change** (see the Cookbook, §7). "Change the fare formula" is a
  pure-function edit in L0 with a unit test. "Switch databases" is a new L2
  adapter that passes the same conformance suite. The layers *are* the index of
  where things live.
- **Fast local signal.** Because inner layers depend only on ports, they run
  against **fakes** with zero infrastructure — the whole domain and every
  use-case are testable in milliseconds on a laptop. Tight loop = good LLM loop.
- **Can't reach sideways.** The Dependency Rule is machine-enforced (§5). If the
  model tries to `import db` from the domain to take a shortcut, the gate rejects
  it. The architecture pushes back before the human has to.
- **Determinism.** Clock, randomness, IDs, and time all come through ports, so
  tests are reproducible and diffs are trustworthy — an LLM's change either moves
  the assertion or it doesn't; no flakiness to launder a real regression.
- **Small blast radius.** The costliest, riskiest logic (concurrency,
  money, security) lives as *pure* rules in L0 (exhaustively property-tested) and
  *one* real adapter behind *one* conformance suite. Nothing else can be
  affected by changing it.

> If a task makes you edit an inner layer to change something outer — or edit
> three layers for one feature — **stop. You are fighting the architecture, or
> the layering is wrong.** That friction is a design signal, not an obstacle to
> route around.

---

## 4. The three test tiers are mandatory — and map onto the layers

This is the core of the doctrine. **Each tier owns a set of layers and a source
of truth.** Every layer is covered by exactly one tier as its *primary* owner.
No layer is untested; no tier is optional.

```
        SYSTEM  ◄── few, slow, real everything ─────────  L4 + the contract, black-box
      ─────────────────────────────────────────────────
     INTEGRATION ◄── some, real infra where it counts ──  L2 (real+fake), L3 (fakes), contract
   ─────────────────────────────────────────────────────
  UNIT ◄──────── many, pure, milliseconds ─────────────  L0, L1 shapes, view-core
```

### Tier 1 — UNIT (owns L0, defines L1)

- **What:** Every pure module gets property tests and example tests. Where a
  reference answer exists (a spec, a formula, a hand-worked case), assert against
  it as an **oracle**, not against your own implementation.
- **Runs against:** nothing. No DB, no network, no clock, no DOM. Milliseconds.
- **Mandatory rule:** a domain / view-core module with no unit test is a build
  failure. Business rules are proven here or nowhere.
- **Why it's the base:** this is where correctness is cheap to establish and an
  LLM gets its fastest, most trustworthy signal.

### Tier 2 — INTEGRATION (owns L2, L3, and the contract)

Three distinct duties, all mandatory:

- **Port conformance.** Every port has **one** conformance suite, run against
  **both** its real and its fake adapter. Same assertions, both implementations —
  this is what guarantees the fake is a faithful stand-in, which is what makes
  the fast inner tests trustworthy. The real adapter runs against **real infra**
  (a throwaway Postgres in a container, a real SMTP catcher), never a mock of it.
- **Use-case orchestration.** Every use-case is tested against **all-fake**
  adapters (fast, deterministic) — this is where multi-step intent, error paths,
  and *concurrency* semantics are pinned. Add a thin real-infra pass for the one
  or two use-cases whose correctness depends on real transactional behaviour.
- **Contract conformance.** The backend proves its routes emit the schema; the
  frontend proves its client accepts it. Both sides test against the *shared*
  contract artifact, so a breaking change fails a build on whichever side caused it.
- **Runs against:** real infrastructure for adapters and the contract; fakes for
  use-cases. Seconds, not milliseconds.

### Tier 3 — SYSTEM / E2E (owns L4 + the whole assembled app)

- **What:** The real stack, wired for real, driven black-box through
  representative user journeys — including the nasty ones (concurrent writes,
  auth failures, payment declines). Browser → API → DB, or API → DB for a
  headless service.
- **Runs against:** the whole thing, exactly as shipped (`docker-compose up`).
  The composition roots — the only code no other tier exercises directly — are
  proven here.
- **Mandatory rule:** at least the primary happy path and every
  correctness-critical hazard (money, concurrency, authz) has a system test.
  Keep the set small; each one is expensive. Depth lives below, in Tiers 1–2.

### The load-bearing consequence

Because the tiers align with the layers, **the tests tell an LLM where a change
belongs and whether it worked, in one motion.** A change to a pure rule is a
Tier-1 edit; if a Tier-1 test doesn't cover it, the change is in the wrong
layer. Test-tier discipline and layer discipline are the same discipline seen
twice. That alignment is precisely what "test-driven, LLM-friendly" means here —
not "we happen to have tests," but "the tests are the map."

**Workflow (mandatory): red before green.** New behaviour starts as a failing
test in the tier that owns its layer. Then make it pass. Then the gate (§5) runs
every tier. This is the LLM's contract with the codebase.

---

## 5. Enforcement — boundaries you can't run get crossed

Docs describing a boundary do not create one. Three machine gates do.

**(a) The Dependency Rule checker.** A static tool that fails the build on any
import pointing outward, plus the subtler contracts a naive "layers" rule would
legalise:

| Contract | Stops |
|---|---|
| `layers` | any import pointing outward (toward the costly end) |
| `usecases-never-touch-a-concrete-adapter` | L3 importing L2 directly (it may see L1 ports only) — a plain layers rule *permits* this and it's the one that rots a codebase |
| `frameworks-out-of-inner-layers` | ORM / http / React / DOM reaching L0–L1 |
| `composition-root-is-a-sink` | anything importing L4; L4 imports inward only |
| `contract-shared-not-copied` | either side importing the other's internals instead of the shared contract |

**(b) Source-scan tests** for what an import graph can't express — banning, in
inner layers, the tokens that smuggle in cost and nondeterminism: wall-clock
reads (`Date.now`, `new Date`, `time.time`), `Math.random` / `random`, `process.env`
/ `os.environ`, `fetch` / raw sockets, filesystem access. (Comments and string
literals excluded — *naming* an idiom in a docstring isn't a violation.) These
must arrive through an L1 port instead.

**(c) The structural test doctrine** — asserted, not hoped: every port has a
conformance suite; every use-case has a fake-based test; every domain/view-core
module has a unit test. Missing test scaffolding fails the build like missing code.

**Prove the gate is alive.** A `guard` step plants a banned import in an inner
layer (`domain → database`) and asserts the checker rejects it, then cleans up.
An enforcement you never watch fail is an enforcement you don't have.

**One command is the gate.** `check = typecheck + lint + arch + unit + integration`
(system runs in CI, and locally on demand — it needs the stack up). Nothing
merges that hasn't passed `check`. This one command is the entire deal an LLM
has to satisfy; keep it fast enough to run on every change.

---

## 6. Where things go

```
<repo root>/
  README.md                 what it is, how to run it
  FULLSTACK_ARCHITECTURE.md this file — the map and the rules
  PLAN.md                   phased build order + numbered decisions (D1, D2, …)
  docker-compose.yml        one-command run: db + api + web + migrations
  Makefile / package.json   check · lint · arch · test:unit · test:int · test:e2e · guard · guard-arch
  .env.example              every config key, no secrets — real .env is gitignored

  contract/                 the seam: OpenAPI / shared types / SDL — generated, shared
    schema.*                the single source of truth for the API
    generated/              types emitted for both sides (never hand-edited)

  backend/
    domain/       L0  entities, value objects, rules, calculations   → UNIT
    ports/        L1  Repository, Clock, Rng, IdGen, Mailer, …
    adapters/     L2  <thing>.real.* and <thing>.fake.* side by side   → INTEGRATION
    usecases/     L3  one file per intent, ports-only                  → INTEGRATION (fakes)
    app/          L4  http server, routes, DI wiring, config, migrations → SYSTEM
    extensions/   L1.5 (optional) pluggable variants behind a registry  → contract suite each

  frontend/
    view-core/    L0  view-models, formatters, validators, reducers    → UNIT
    ports/        L1  ApiClient, Storage, Clock, Router
    adapters/     L2  api.real.* / api.fake.*, storage.real / storage.fake → INTEGRATION
    ui/           L3  components, hooks, state — ports only             → INTEGRATION (fakes)
    app/          L4  entry, router, providers, env wiring              → SYSTEM

  tests/
    unit/         mirrors domain/ and view-core/
    integration/  port conformance (real+fake), use-cases (fakes), contract
    system/       e2e journeys against docker-compose
    architecture/ the source-scan + structural-doctrine tests of §5
```

Adapters live in **pairs**: `seat_repo.real.ts` + `seat_repo.fake.ts` next to
each other, both subject to the same conformance suite. Seeing the pair is the
point — the fake is documentation of the port's contract you can execute.

---

## 7. The cookbook — to do X, edit only Y

| Task | Do this | Edit nothing else |
|---|---|---|
| Change a business rule / formula | edit the pure function in `domain/` + its unit test | not the DB, not the API |
| Add a field to an entity | `domain/` type + unit test; then contract; then adapters/migration follow the contract | rules stay in L0 |
| Add a new query or command | one file in `usecases/`, wired through existing ports | if you need a new capability, add a **port method** first |
| Swap a database / provider | new `*.real.*` adapter passing the existing conformance suite | zero domain / use-case changes |
| Add an external dependency (email, payments) | new port in `ports/` + real & fake adapters + conformance suite | use-cases call the port |
| Add an API endpoint | contract first, then a `usecases/` intent, then wire a route in `app/` | domain untouched unless the rule is new |
| Change how something looks | `frontend/view-core/` formatter/view-model + unit test; `ui/` renders it | no `fetch` in components |
| Change how the frontend loads data | `frontend/ports/ApiClient` + both adapters | components call the port |
| Add a pluggable variant (payment method, ranking) | new file in `extensions/` with `@register` (§8) | the registry finds it by name |
| Change config / a limit / a toggle | edit config data + `.env.example` | never hardcode in a rule |

If a task isn't on this list, it usually decomposes into rows that are. If it
*can't*, that's the signal to think — not to spread one change across four layers.

---

## 8. Optional L1.5 — Extensions, only when variation is real

Some systems have a genuinely open set of variants: payment methods, ranking
strategies, notification channels, export formats. For those, add a thin
**registry** layer between L1 and L2: each variant is one file that
self-registers under a name (`@register("stripe")`), and a use-case selects one
*by name* through a port. Adding a variant is then a new file that auto-enrols
in the variant contract suite — **edit nothing else.**

Do **not** add this layer speculatively. Two hardcoded `if` branches are
simpler than a registry and a registry is only worth it at the third variant.
Simplicity first; reach for L1.5 when the `if` chain starts to hurt, not before.

---

## 9. Concrete bindings (pick one; the rules above don't change)

The architecture is stack-agnostic. Here is how the abstract pieces bind to real
tools. Any row can be swapped without touching L0–L1.

| Piece | TypeScript | Python | Go / JVM |
|---|---|---|---|
| Dependency-rule checker | dependency-cruiser / eslint-plugin-boundaries | import-linter | go-arch-lint · depguard / ArchUnit |
| Unit tests | Vitest / Jest + fast-check | pytest + Hypothesis | testing + rapid / JUnit + jqwik |
| Integration DB | Testcontainers-postgres | Testcontainers / pytest-postgresql | Testcontainers |
| System / E2E | Playwright | Playwright | Playwright |
| Contract seam | OpenAPI + openapi-typescript / tRPC / Zod | OpenAPI + pydantic / FastAPI | OpenAPI / protobuf |
| Fakes | plain in-memory classes | plain in-memory classes | in-memory structs |
| One-command run | docker-compose | docker-compose | docker-compose |

The invariants that survive every binding: **the Dependency Rule, ports with
paired real+fake adapters, the three test tiers mapped onto the layers, and a
machine gate that fails the build on a violation.** Change the tools freely;
keep those four and you keep both goals.

---

## 10. Smells — you're fighting the architecture when…

- …a feature needs edits in three or more layers. → It's mislayered, or it's
  really three features.
- …a use-case imports a concrete adapter "just this once." → Add or use a port.
- …a domain test needs a database to run. → Cost leaked inward; push it behind a port.
- …a component calls `fetch` directly. → Route it through `ApiClient`.
- …a test is flaky. → Nondeterminism (clock/rng/network) escaped its port.
- …the fake and the real adapter disagree in production. → They don't share one
  conformance suite; make them.
- …you reach for a registry with one variant. → Delete it; use an `if`.
- …you can't say which test tier owns a change. → The change is in the wrong layer.

Each smell has a fixed remedy, and the remedy is always "move the cost outward,
keep the core pure, let the gate check it." That is the whole architecture in
one sentence.
