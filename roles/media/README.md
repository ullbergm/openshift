# Media Server Role

The media role provides a comprehensive media management and automation stack for organizing, downloading, and serving media content. This role includes applications for automated TV show and movie management, subtitle handling, collection gap analysis, and comic book management.

## Applications

### Core Media Management

- **Sonarr** - TV show management and automation
- **Radarr** - Movie management and automation
- **Kapowarr** - Comic book and manga management

### Specialized Tools

- **Bazarr** - Subtitle management for movies and TV shows
- **Gaps** - Plex collection gap analysis and recommendations

## Architecture Overview

This media stack follows the \*arr application pattern with automated content discovery, quality management, and organization. All applications are configured to work together seamlessly with shared storage and consistent naming conventions.

### Data Flow

1. **Content Discovery** - Sonarr/Radarr monitor for new releases
2. **Download Management** - Integration with download clients
3. **Post-Processing** - Automatic organization and renaming
4. **Subtitle Management** - Bazarr automatically downloads subtitles
5. **Quality Analysis** - Gaps identifies missing content in collections

## Configuration Guidelines

### Shared Storage

- All applications use persistent volumes for configuration
- Download directories are shared between apps and download clients
- Media libraries are in a shared folder structure
  ```text
  data/
  ├── torrents/                    # Download client working directory
  │   ├── books/                   # Comic/book downloads
  │   ├── movies/                  # Movie downloads
  │   ├── music/                   # Music downloads
  │   └── tv/                      # TV show downloads
  ├── usenet/                      # Usenet download management
  │   ├── incomplete/              # Active downloads
  │   └── complete/                # Completed downloads
  │       ├── books/
  │       ├── movies/
  │       ├── music/
  │       └── tv/
  └── media/                       # Final organized media library
      ├── books/                   # Comics and ebooks
      ├── movies/                  # Organized movie library
      ├── music/                   # Music library
      └── tv/                      # Organized TV show library
  ```

### Networking

- Each application runs in its own namespace
- OpenShift Routes provide external access with automatic TLS
- Internal service-to-service communication for API integration
