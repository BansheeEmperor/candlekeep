# ROM Testing Backward Planning Template

## 1. Purpose & How to Use This Template

This is a **QA planning document**. It covers the test planning lifecycle from requirements handoff to ROM freeze sign-off. Development milestones (firmware, platform software, emulator) appear as tracked external dependencies, not owned milestones — QA flags risks, PM drives cross-functional resolution.

A future phase (planned for AL14) will expand this into a full project planning document covering the entire delivery chain.

ROM testing projects share a common failure pattern: dependency delays and infrastructure gaps surface late, when there is no schedule buffer left to absorb them. This template exists to make those risks visible early enough to act on.

The approach is backward planning — start from the fixed end date (tape-out or sign-off) and work backward to define when each dependency and infrastructure component must be ready. Dates are expressed as offsets from tape-out: **TO-NWW** means N work weeks before tape-out.

**When to apply this template:**

* At project kickoff, before implementation begins
* Any time the tape-out date changes significantly

**How to use it:**

1. Confirm the tape-out target date with the program team. If tape-out is unknown, use the ROM code freeze date as the anchor and flag tape-out as AT RISK in the dependency register until confirmed.
2. Fill in the RACI with core attendees present (see section 2)
3. Derive milestone dates from the offset column using your tape-out date
4. Provide PM with the required dependency list; PM secures committed dates from each external team and populates the dependency register
5. Flag any dependency where the committed date doesn't meet the required offset — document a mitigation plan before proceeding past the prior milestone
6. Review at each milestone gate; update if scope or dates change

**Notation:** TO-NWW = tape-out minus N work weeks. Example: if tape-out is December 1st, TO-8WW is approximately October 6th.

**Template ownership:** This template is owned by the QA Lead. Post-project retrospectives should feed gaps back into the template.

---

## 2. RACI

Define ownership at kickoff. Every row in the milestone chain and dependency register must have a named Responsible owner before the project proceeds.

**Role definitions:**

| Role | Description |
|---|---|
| QA Lead | Document owner. Owns test planning, development, execution, sign-off, and CI infrastructure. Escalates cross-functional dependency risks to PM |
| PM | Escalation path for cross-functional dependency resolution. Not the document owner |
| Architect | Owns requirements, design documents, and technical scope definition |
| FW Lead | Owns firmware delivery and API readiness |
| Emulation Developer | Owns emulator/VP software for the current chip generation; consulted async |
| Platform Software Lead | Owns platform software (e.g., Linux) driver and kernel patch delivery |

**Core attendees** (kickoff meeting must not proceed without these roles filled): PM, Architect, QA Lead, FW Lead.

**Consulted stakeholders** (own specific milestones but outside regular meeting cadence): Send RACI for async review and acknowledgment within 5 business days of kickoff (email is sufficient). No response triggers escalation to PM. Their rows in the milestone chain are not finalized until acknowledgment is received.

> Note: Add or remove roles to match your project. The key requirement is that every milestone has a named owner — "team" is not an owner.

---

## 3. Layer 1: Milestone Chain

Milestones are ordered from earliest to latest. Offsets are starting points — adjust based on your project's actual lead times. AL12 reference offsets are provided in the appendix.

For each milestone, answer:

* What must be true before this milestone starts? (Entry criteria)
* What must be true before this milestone is complete? (Exit criteria)
* Who escalates if this milestone is missed, and to whom?

| # | Milestone | Suggested Offset | Responsible | Entry Criteria | Exit Criteria | Escalation |
|---|---|---|---|---|---|---|
| 1 | QA kickoff prerequisites ready | TO-20WW or earlier | Architect + PM | Initial scope drafted | Design documents and requirements handed off to QA Lead; QA Lead confirms sufficient detail to begin test planning | PM → Architect |
| 2 | External dependencies committed | TO-16WW | PM | Requirements signed off | All external dependencies have committed dates in the register via tracked ticket; QA Lead confirms no blocking gaps before test planning begins | PM |
| 3 | Infrastructure validated (VP + emulator CI green) | TO-12WW | QA Lead | Emulator available from Emulation Developer | Weekly CI passing on both VP and emulator; sufficient QA and test resources allocated to execute tests independently without single-resource dependency (define headcount per project) | QA Lead → PM |
| 4 | Test development complete | TO-8WW | QA Lead | All dev dependencies delivered and merged | All tests passing on VP; code reviewed and merged to the project's main branch | QA Lead → PM |
| 5 | VP execution complete | TO-6WW | QA Lead | Test development complete | All VP tests passing; report drafted; open defects triaged | QA Lead → PM |
| 6 | Emulator execution complete | TO-3WW | QA Lead | VP execution complete | All emulator tests passing; open defects triaged and resolved or accepted | QA Lead → PM |
| 7 | ROM freeze / sign-off | TO-0 | QA Lead + FW Lead | Emulator execution complete | Test report approved; no open Sev1/Sev2 defects | — |

**Gate enforcement:** PM calls gate reviews for milestones 1–2 and acts as escalation path throughout. QA Lead calls gate reviews for milestones 3–7. Either role has authority to block progression if exit criteria are not met. The escalation chain above PM (e.g., Software Director, Group Manager) is defined per project and must be documented at kickoff.

**Operational notes:**

* Every milestone is a risk gate. Problems surfaced at milestones 1–3 are recoverable with enough buffer to act; problems surfaced at milestone 4 or later compress or eliminate recovery options. The earlier a risk is visible, the more mitigation paths remain open.
* A milestone is not complete on the date — it's complete when exit criteria are met. If exit criteria aren't met, the milestone is missed regardless of the calendar date.
* If any milestone slips, re-derive all subsequent dates immediately. Don't absorb slip silently.

---

## 4. Layer 2: Dependency Register

External dependencies are the most common source of unrecoverable schedule slip. This layer makes them visible and trackable from kickoff.

**How to populate this layer:**

1. List every deliverable your project needs from a team you don't control
2. Determine the latest date you can receive it and still meet the downstream milestone (Required By)
3. Get a written commitment from the owning team in the form of a tracked ticket with a named owner and due date — verbal commitments don't count
4. Flag any dependency where committed date is later than Required By as **AT RISK** immediately; don't wait to see if it resolves itself
5. For every AT RISK dependency, document a mitigation plan before proceeding past the prior milestone

| # | Dependency | Required By Milestone | Required By (Offset) | Owner Team | Committed Date | Status | Mitigation If Late |
|---|---|---|---|---|---|---|---|
| — | _(example: platform software support)_ | _(e.g., Test dev complete)_ | _(set per project)_ | — | — | — | _(example: pivot to component-level tests that bypass the dependency)_ |
| — | _(example: emulator availability)_ | _(e.g., Infrastructure validated)_ | _(set per project)_ | — | — | — | _(example: extend VP-only coverage; escalate to emulator team lead)_ |
| — | _(add rows as needed)_ | | | | | | |

**Status values:** `On Track` / `AT RISK` / `Delayed` / `Delivered`

**AT RISK rule:** If committed date doesn't meet Required By offset, status is AT RISK. A mitigation plan is required in writing before the project proceeds past the prior milestone. AT RISK dependencies are reviewed at every subsequent milestone gate until resolved.

**On unmerged code:** Dependencies are not considered delivered until patches are merged to mainline. Side-releases and unmerged branches do not satisfy the committed date.

---

## 5. Risk Flag Rule

A dependency or milestone is flagged **AT RISK** when any of the following are true:

* Committed date is later than the Required By offset
* Exit criteria cannot be verified (e.g., no CI, no test report, no written acknowledgment, etc.)
* Owner is unassigned or unresponsive after 5 business days
* A milestone is missed without a revised date and mitigation plan

**What's required when AT RISK is raised:**

1. Document the risk in the dependency register or milestone chain immediately — don't wait for the next meeting
2. Define a mitigation plan: what's the fallback, who owns it, by when
3. Escalate to PM within 2 business days if no mitigation path exists
4. Review at every subsequent milestone gate until resolved or accepted

**AT RISK is not a failure state** — it's an early warning. The failure state is an undetected risk that surfaces on the critical path with no time to mitigate. Raising AT RISK early is the correct behavior this template is designed to encourage.

---

## Appendix: AL12 Citadel ROM Testing — Worked Example

This appendix shows how AL12 should have applied this template at kickoff. Use it as a reference when instantiating the template for a new project, not as a starting point to copy.

### RACI — AL12

| Role | Name |
|---|---|
| PM | @olgagg |
| Architect | @erezt |
| QA Lead | @raalgaw |
| FW Lead | @ohanam |
| Emulation Developer | @moshebar |
| Linux Lead | @itamark |

**Note:** CI infrastructure enablement for emulator tests must be explicitly assigned at kickoff. Assign to Linux Lead (@itamark) — do not leave this implicit or assumed.

### Layer 1: Milestone Chain — AL12

Tape-out: January 11, 2026. Planned sign-off: October 20, 2025 (TO-12WW).

| # | Milestone | Offset | Planned Date |
|---|---|---|---|
| 1 | QA kickoff prerequisites ready | TO-20WW | TBD (@raalgaw) |
| 2 | External dependencies committed | TO-16WW | TBD (@raalgaw) |
| 3 | Infrastructure validated (VP + emulator CI green) | TO-12WW | TBD (@raalgaw) |
| 4 | Test development complete | TO-8WW | TBD (@raalgaw) |
| 5 | VP execution complete | TO-6WW | TBD (@raalgaw) |
| 6 | Emulator execution complete | TO-3WW | TBD (@raalgaw) |
| 7 | ROM freeze / sign-off | TO-0 | October 20, 2025 |

### Layer 2: Dependency Register — AL12

| # | Dependency | Required By Milestone | Required By (Offset) | Owner | Committed Date | Status | Mitigation If Late |
|---|---|---|---|---|---|---|---|
| 1 | Linux driver support | Test dev complete (#4) | TO-14WW | @itamark | TBD (@raalgaw) | On Track | Pivot to CVOS-based tests for component-level coverage while waiting |
| 2 | Emulator availability + CI enablement | Infrastructure validated (#3) | TO-13WW | @itamark | TBD (@raalgaw) | On Track | Extend VP-only coverage; escalate to @moshebar |
| 3 | Linux + DT patches merged to mainline | Test dev complete (#4) | TO-14WW | @itamark | TBD (@raalgaw) | On Track | Block test execution until merged; escalate to @olgagg |
