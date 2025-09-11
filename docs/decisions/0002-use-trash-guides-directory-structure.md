---
status: "accepted"
date: 2025-09-11
decision-makers:
 - @ullbergm
---

# Adopt TRaSH-Guides directory structure for media applications

## Context and Problem Statement

The media stack (Sonarr, Radarr, Bazarr, Kapowarr, and related tools) needs a consistent directory layout for downloads, post-processing, and the final media library. Without a shared convention, container path mappings, application configuration, and automation become fragile and error-prone. We need a clear standard that works well with the \*arr ecosystem and our OpenShift/Helm structure.

## Decision Drivers

- Interoperability with the \*arr ecosystem and Plex/Emby/Jellyfin
- Predictable container path mappings across multiple applications
- Clear separation between transient downloads and the curated media library
- Community alignment and ease of onboarding (widely documented patterns)
- Simpler automation/docs in charts and role templates
- Backup hygiene (exclude transient downloads; keep media policies predictable)

## Considered Options

- TRaSH-Guides directory structure
- Ad-hoc, app-specific directory layouts per application
- Flat structure with minimal separation (single-level folders)
- Downloader-centric layout that leaks implementation details into all apps

## Decision Outcome

Chosen option: "TRaSH-Guides directory structure", because it is the de-facto community standard for \*arr-based media stacks, minimizes path-mapping issues between containers, and cleanly separates downloads from the final media library.

### Canonical layout used

```text
/data/
├── torrents/                    # BitTorrent client working directory
│   ├── tv/
│   ├── movies/
│   └── books/
├── usenet/                      # Usenet client working directory
│   ├── incomplete/
│   └── complete/
│       ├── tv/
│       ├── movies/
│       └── books/
└── media/                       # Final organized media library
    ├── tv/
    ├── movies/
    ├── music/
    └── books/
```

Notes:

- Each application mounts the same base path (e.g., `/data`) to avoid path translation problems.
- Config/state lives on separate per-app config volumes; the structure above focuses on shared data.
- Where supported, the layout enables hardlinking from completed downloads to the library; where not supported (e.g., across filesystems/NFS), copy/move still works predictably.

### Consequences

- Good, because it aligns with widely adopted community guidance and most upstream docs/examples.
- Good, because it reduces misconfiguration risks and simplifies application handoffs (download → process → library).
- Good, because backup policies are easier to reason about (exclude transient `torrents/` and `usenet/incomplete/`).
- Bad, because existing deployments may require one-time migration to the new structure.
- Bad, because the convention can feel prescriptive for non-\*arr tooling.

### Confirmation

- Role and chart reviews verify consistent volume mounts and path usage across media apps (common `/data` root; app-specific config volumes separate).
- Media apps are able to import completed downloads and organize into `/data/media/...` without custom path remapping.
- Kasten backup/exclusion labeling can target only the durable media library and skip transient download paths.

## Pros and Cons of the Options

### TRaSH-Guides directory structure

- Good, because it is well-documented and community-standardized.
- Good, because it minimizes cross-container path mapping issues.
- Good, because it separates transient and durable data cleanly.
- Neutral, because it assumes a common mount point; charts already enforce that.
- Bad, because migration may be needed for legacy layouts.

### Ad-hoc per-app layouts

- Good, because highly flexible per team preference.
- Neutral, because small setups can "just work" initially.
- Bad, because inconsistencies cause brittle automation and confusing path mappings.
- Bad, because onboarding and support are harder without common conventions.

## More Information

- TRaSH-Guides: [https://trash-guides.info/](https://trash-guides.info/)
- Hardlinks and directory layout background: [https://trash-guides.info/Hardlinks/](https://trash-guides.info/Hardlinks/)

This ADR complements the media role documentation and the storage/backup patterns described in the repository standards. The intent is to keep app configuration simple and repeatable while avoiding common pitfalls around container path translation and download vs. library separation.
