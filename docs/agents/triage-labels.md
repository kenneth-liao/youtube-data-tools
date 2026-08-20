# Triage Labels

This file defines the canonical tracker roles and maps them to GitHub labels.

## Category roles

| Canonical role | GitHub label | Meaning |
| --- | --- | --- |
| `bug` | `bug` | Something is broken |
| `enhancement` | `enhancement` | New feature or improvement |

## Artifact marker

| Canonical role | GitHub label | Meaning |
| --- | --- | --- |
| `spec` | `spec` | Specification |

The `spec` marker is authoritative. A `[SPEC]` title prefix is only a display aid.

## Readiness and disposition roles

| Canonical role | GitHub label | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Maintainer needs to evaluate this request |
| `needs-info` | `needs-info` | Waiting on the reporter |
| `ready-for-tickets` | `ready-for-tickets` | Settled spec awaiting decomposition |
| `ready-for-agent` | `ready-for-agent` | Executable ticket an agent can complete |
| `ready-for-human` | `ready-for-human` | Executable ticket requiring a human step |
| `wontfix` | `wontfix` | Request will not be actioned |

Every triaged item has one category role. Every open actionable item has one readiness or disposition role. After decomposition, a parent keeps `spec` and its category but has no readiness role; its children carry the next actions.

Use `ready-for-agent` only when an agent can finish the work from repository and tracker context with ordinary authorized tools.

Use `ready-for-human` when completion inherently requires personal authentication, subjective qualification, privileged or irreversible production access, legal/compliance/security approval, or a decision that cannot be reduced to approved acceptance criteria. Split agent preparation from the human action when each can be verified independently, and record the specific human step as the readiness rationale.
