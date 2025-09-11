---
status: "accepted"
date: 2025-09-11
decision-makers:
 - @ullbergm
---

# Standardize a common `/data` mount across all media containers

## Context and Problem Statement

The media stack (Sonarr, Radarr, Bazarr, Kapowarr, etc.) coordinate on shared files that flow from download clients to post-processing and finally into the organized media library. We need a predictable, consistent path layout inside every container so that move/rename and hardlink operations work reliably across apps.

Two patterns were considered:

- Mount one common root (`/data`) into all media pods.
- Mount only the specific subfolders a pod needs (e.g., just `/data/usenet/complete/movies` for Radarr).

The second option often results in “move” operations degrading to copy, because source and destination are not the same mount or path from the container’s perspective. This increases I/O, takes longer, and temporarily doubles disk usage. We want to avoid that and keep the pipeline efficient and stable.

## Decision Drivers

- Enable atomic rename/move and hardlink operations (avoid copy-on-move)
- Cross-container path consistency and simpler configuration
- Better performance and reduced storage churn during post-processing
- Fewer path-translation bugs between apps
- Straightforward documentation and chart defaults
- Alignment with ADR-0002 TRaSH-Guides directory structure

## Considered Options

- Standardize on a single shared mount point `/data` for all media containers
- Mount only the specific subfolders each pod needs (narrow per-app mounts)
- Use per-app base paths and rely on app-level path remapping/translation

## Decision Outcome

Chosen option: "Standardize on a single shared mount point `/data` for all media containers", because it ensures that source and destination paths are on the same filesystem within each container, enabling atomic rename/move and hardlink operations. This minimizes unnecessary copying, improves performance, reduces temporary storage bloat, and simplifies configuration across the media stack.

### Consequences

- Good, because move/rename and hardlinks work reliably (no copy-on-move), making post-processing fast and storage-efficient.
- Good, because every app can reference the same canonical paths and documentation is simpler.
- Good, because it complements ADR-0002’s TRaSH-Guides layout under a single `/data` root.
- Good, because backup and retention policies can target stable subpaths consistently.
- Bad, because pods may see a broader directory tree than the strict minimum they need.
- Bad, because careful ownership/permissions and read-only mounts (where possible) are required to uphold least privilege.

### Confirmation

- Chart and role reviews verify that all media apps mount the same PVC at the same in-container path (`/data`).
- App logs (e.g., Sonarr/Radarr) show hardlink or atomic move operations rather than copy when importing.
- Smoke test: moving files from download directories to the library within `/data` does not spike write I/O proportional to file size, indicating rename/hardlink usage.

## Pros and Cons of the Options

### Single shared `/data` mount for all media containers

- Good, because it preserves same-filesystem semantics needed for rename/hardlink.
- Good, because it reduces cross-app path translation and configuration drift.
- Good, because it consolidates documentation and chart values.
- Neutral, because it standardizes on one convention; flexibility remains via subpaths.
- Bad, because broader visibility requires thoughtful permissions and, for some apps, read-only mounts.

### Narrow per-app mounts (only specific subfolders)

- Good, because it follows least privilege by exposing only what each pod needs.
- Neutral, because it can work for small/siloed setups.
- Bad, because moves often become copies when source/destination are different mounts, increasing I/O and time.
- Bad, because it complicates cross-app coordination and increases path-translation issues.

### Per-app base paths with path remapping/translation

- Good, because it allows custom layouts per application.
- Neutral, because many apps support mapping tables.
- Bad, because mappings are brittle across updates and operators; easy to misconfigure.
- Bad, because it does not guarantee same-filesystem semantics, so copies may still occur.

## More Information

- See ADR-0002: Adopt TRaSH-Guides directory structure for media applications, which defines the canonical `/data` layout used by the stack.
- Operational guidance: where possible, mount `/data` read-only in viewer apps (e.g., media servers) and read/write in automation apps that need to move/rename files. Enforce correct UID/GID ownership and permissions per subdirectory.
