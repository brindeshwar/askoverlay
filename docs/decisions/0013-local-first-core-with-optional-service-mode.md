# ADR-0013: A local-first core, with a designed but unbuilt service mode

- Status: Proposed
- Date: 2026-10-12
- Related: Designed in [HLD](../04-architecture/hld.md) and [scaling and operations](../04-architecture/scaling-and-operations.md).

## Context

The owner wants a professional system design including load balancing and scaling. A solo, part-time project cannot afford to
build and operate a multi-tenant platform before anyone uses it, yet a design that cannot scale would be a poor foundation.
Privacy also matters: tests touch applications and credentials the user may not want to send to a third party. The binding
constraint at scale is the model provider's quota, not compute (scaling document, section 5).

## Options considered

1. **Hosted service first.** Wide reach; large up-front cost (accounts, multi-tenancy, operations, security exposure) with no
   proven demand.
2. **Local only, no scaling design.** Cheapest; risks an architecture that cannot grow.
3. **Local-first core (runs in one process, with the user's own key), and a service mode that is fully *designed* but built
   only when a trigger is met.**

## Decision

We will build **option 3**. The core engine uses ports and adapters so the same code runs in one process (local and CI) and in a
worker pool (service). Service mode is specified (load balancer, stateless API, queue and workers, quota manager, autoscaling,
observability, recovery) and tracked as release R5, to be built only when a trigger in scaling document section 11 is reached.

## Consequences

- R1 to R4 stay small and fast to build; no infrastructure to operate.
- No hosted data path means strong default privacy.
- Design constraints are honoured from day one: stateless adapters, event-sourced runs, idempotent starts, explicit leases.
- Risk that the unbuilt design hides problems; mitigated by a synthetic runner that can load-test the platform without model
  cost when R5 starts, and by calling every capacity number an assumption until measured.

## How we will know it was right

R1 to R4 ship without service-mode code; when R5 starts, the core needs only a new storage adapter and a scheduler adapter, not
changes to the agent, verdict or policy code.
