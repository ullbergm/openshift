---
status: "accepted"
date: 2025-09-11
decision-makers:
 - @ullbergm
---

# Use OpenShift for the platform

## Context and Problem Statement

We need to choose a Kubernetes platform to develop and validate this framework against as the reference environment.

## Decision Drivers

- access to the platform and relevant code artifacts
- learning goals aligned with day-to-day work
- availability of similar solutions in the open-source ecosystem

## Considered Options

- OpenShift
- OKD

## Decision Outcome

Chosen option: "OpenShift", because it allows me to learn how to use the platform I support at work.

### Consequences

- Good, because it matches what I do for a living.
- Bad, because it requires access to a licensed version.

### Confirmation

- Architecture and chart reviews confirm the use of OpenShift-specific resources where appropriate (for example, Route and SecurityContextConstraints).
- The repository’s validation tasks should pass when run against an OpenShift target, confirming manifests render and basic checks succeed.

## Pros and Cons of the Options

### OpenShift

- Good, because it matches what I do for a living.
- Bad, because it is not free.

### OKD

- Good, because it matches what I do for a living.
- Bad, because the deployment model doesn't work without a lot of workarounds.

## More Information

I really wanted to do a fully open-source OKD version but unfortunately it is not as supportable as the OpenShift version.
