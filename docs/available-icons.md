# Available Icons for Applications

This document lists the available icons found for applications in this repository, particularly focusing on CBI (Container Base Images) icons.

**Last Updated:** October 5, 2025
**Tool Used:** `./scripts/find-icons.py` and `./scripts/check-cbi-icons.py`

## Summary

- **Total Applications:** 47
- **CBI Icons Available:** 10 (21%)
- **No CBI Icons:** 37 (79%)

## Applications WITH CBI Icons ✅

The following applications have icons available in the CBI collection:

| Application  | Icon Reference     | Notes                       |
| ------------ | ------------------ | --------------------------- |
| bazarr       | `cbi:bazarr`       | Media subtitle management   |
| flaresolverr | `cbi:flaresolverr` | Proxy server for Cloudflare |
| jellyseerr   | `cbi:jellyseerr`   | Media request management    |
| metube       | `cbi:metube`       | YouTube downloader          |
| overseerr    | `cbi:overseerr`    | Media request management    |
| plex         | `cbi:plex`         | Media server                |
| prowlarr     | `cbi:prowlarr`     | Indexer manager             |
| radarr       | `cbi:radarr`       | Movie collection manager    |
| sabnzbd      | `cbi:sabnzbd`      | Usenet binary downloader    |
| sonarr       | `cbi:sonarr`       | TV series management        |

## Applications WITHOUT CBI Icons (Alternative Icons Available)

For applications without CBI icons, here are some alternatives found in other icon collections:

### Home Automation

| Application    | Best Alternative     | Collection            |
| -------------- | -------------------- | --------------------- |
| home-assistant | `mdi:home-assistant` | Material Design Icons |
| node-red       | _(search needed)_    | -                     |
| zwavejs2mqtt   | _(search needed)_    | -                     |

### Media Applications

| Application | Best Alternative            | Collection | Notes                    |
| ----------- | --------------------------- | ---------- | ------------------------ |
| lidarr      | No direct match found       | -          | May need custom icon     |
| readarr     | _(search needed)_           | -          |                          |
| tautulli    | `arcticons:tautulli-remote` | Arcticons  | Remote variant available |
| kavita      | _(search needed)_           | -          |                          |
| kapowarr    | _(search needed)_           | -          |                          |
| pinchflat   | _(search needed)_           | -          |                          |
| posterizarr | _(search needed)_           | -          |                          |
| recyclarr   | _(search needed)_           | -          |                          |
| gaps        | _(search needed)_           | -          |                          |
| huntarr     | _(search needed)_           | -          |                          |

### Productivity

| Application | Best Alternative  | Collection | Notes |
| ----------- | ----------------- | ---------- | ----- |
| bookmarks   | _(search needed)_ | -          |       |
| cyberchef   | _(search needed)_ | -          |       |
| excalidraw  | _(search needed)_ | -          |       |
| it-tools    | _(search needed)_ | -          |       |
| startpunkt  | _(search needed)_ | -          |       |

### Infrastructure & Operators

| Application                         | Best Alternative         | Collection | Notes |
| ----------------------------------- | ------------------------ | ---------- | ----- |
| certificates                        | _(generic cert icon)_    | -          |       |
| custom-error-pages                  | _(generic error icon)_   | -          |       |
| democratic-csi                      | _(search needed)_        | -          |       |
| emqx-operator                       | _(search needed)_        | -          |       |
| external-secrets-operator           | _(search needed)_        | -          |       |
| gatus                               | _(search needed)_        | -          |       |
| generic-device-plugin               | _(search needed)_        | -          |       |
| goldilocks                          | _(search needed)_        | -          |       |
| intel-gpu-operator                  | _(search needed)_        | -          |       |
| k10-kasten-operator                 | _(search needed)_        | -          |       |
| keepalived-operator                 | _(search needed)_        | -          |       |
| openshift-nfd                       | _(search needed)_        | -          |       |
| system-reservation                  | _(search needed)_        | -          |       |
| disable-master-secondary-interfaces | _(generic network icon)_ | -          |       |
| disable-worker-secondary-interfaces | _(generic network icon)_ | -          |       |

### AI Applications

| Application | Best Alternative  | Collection | Notes |
| ----------- | ----------------- | ---------- | ----- |
| litellm     | _(search needed)_ | -          |       |
| ollama      | _(search needed)_ | -          |       |
| open-webui  | _(search needed)_ | -          |       |

### Radio

| Application | Best Alternative  | Collection | Notes             |
| ----------- | ----------------- | ---------- | ----------------- |
| adsb        | _(search needed)_ | -          | Aircraft tracking |

## How to Use

To add an icon to an application's Helm chart `values.yaml`:

```yaml
icon: "cbi:plex"  # For applications with CBI icons
# OR
icon: "mdi:home-assistant"  # For alternative collections
```

## Icon Collections Priority

The `find-icons.py` script prioritizes the following icon collections:

1. **simple-icons** (100) - Brand and company logos
2. **logos** (95) - Technology logos
3. **mdi** (90) - Material Design Icons
4. **devicon** (88) - Developer-focused icons
5. **fa6-brands** (85) - Font Awesome brands
6. **lucide** (80) - Clean, consistent icons
7. **tabler** (75) - Simple stroke icons
8. **heroicons** (70) - UI icons

## Searching for Icons

To search for icons for a specific application:

```bash
# Search in all collections
./scripts/find-icons.py "application-name" --max-results 10

# Search only in CBI collection
./scripts/find-icons.py "application-name" --collections cbi

# Search with details
./scripts/find-icons.py "application-name" --details

# Export results to JSON
./scripts/find-icons.py "application-name" --export results.json

# Export to Markdown
./scripts/find-icons.py "application-name" --export-md results.md
```

To check all applications for CBI icons:

```bash
python3 ./scripts/check-cbi-icons.py
```

## Icon Validation

After adding icons to your values.yaml files, validate them:

```bash
./scripts/validate-icons.sh --online
```

## Notes

- CBI (Container Base Images) icons are specifically designed for self-hosted applications
- The CBI collection has excellent coverage for media management applications (\*arr stack)
- For infrastructure components and operators, generic icons from MDI or Tabler might be more appropriate
- Some niche applications may not have dedicated icons and might need custom SVG icons
