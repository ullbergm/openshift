# Icon Search Script Documentation

## Overview

The `find-icons.sh` script searches for icons using the Iconify API with a preference for simple-icons (brand logos). This tool helps you find appropriate icons for applications in your Kubernetes cluster.

## Usage

```bash
./scripts/find-icons.sh <application-name> [options]
```

### Options

- `-h, --help`: Show help message
- `-v, --verbose`: Enable verbose output with detailed icon information
- `--timeout SECONDS`: Set API request timeout (default: 10 seconds)
- `--max-results N`: Maximum number of results per collection (default: 10)

## Examples

### Basic Usage

```bash
# Search for Plex icons
./scripts/find-icons.sh plex

# Search for Jellyfin icons with verbose output
./scripts/find-icons.sh jellyfin --verbose

# Search for Docker icons with custom limits
./scripts/find-icons.sh docker --max-results 5
```

### Multi-word Applications

```bash
# Use quotes for multi-word application names
./scripts/find-icons.sh "visual studio code"
./scripts/find-icons.sh "home assistant"
```

## Icon Collections (Search Priority)

The script searches these icon collections in order of preference:

1. **simple-icons** - Brand and company logos (preferred for applications)
2. **mdi** - Material Design Icons (general purpose icons)
3. **lucide** - Clean, consistent icons
4. **tabler** - Outline icons
5. **heroicons** - Tailwind CSS icons

## Output Format

The script returns icons in the format: `collection:icon-name`

Examples:

- `simple-icons:plex`
- `mdi:server`
- `lucide:home`

## Integration with Helm Charts

Use the returned icon names directly in your `values.yaml` files:

```yaml
# values.yaml
icon: simple-icons:plex  # Preferred for brand icons
# or
icon: mdi:plex          # Alternative if simple-icons not available
```

## Icon Validation

After selecting an icon, validate it using the existing validation script:

```bash
./scripts/validate-icons.sh --online
```

## Tips

### For Brand Applications

- Search using the exact brand name (e.g., "plex", "jellyfin", "prometheus")
- simple-icons usually has the best brand logos

### For Generic Applications

- If no brand icon exists, search for functional terms
- Consider using generic MDI icons like:
  - `mdi:server` for server applications
  - `mdi:monitor` for monitoring tools
  - `mdi:database` for database applications
  - `mdi:application` for general applications

### Troubleshooting

- If no results found, try:
  - Shorter terms (e.g., "code" instead of "visual studio code")
  - Alternative names (e.g., "vscode" instead of "visual studio code")
  - Generic functional terms (e.g., "media" instead of specific media app name)

## Dependencies

The script requires:

- `curl` - for API requests
- `jq` - for JSON parsing

These are typically available in most Linux environments including the dev container.

## API Rate Limits

The Iconify API is generally free and has generous rate limits for reasonable usage. The script includes:

- 10-second timeout per request
- Sequential searching (not parallel) to be respectful of the API
- Minimal requests (only searches collections that are configured)

## Integration with Existing Workflow

This script complements the existing icon validation workflow:

1. **Search**: Use `find-icons.sh` to discover available icons
2. **Select**: Choose appropriate icon from results
3. **Configure**: Add icon to your Helm chart's `values.yaml`
4. **Validate**: Run `validate-icons.sh --online` to verify the icon works

## Examples with Real Applications

### Media Stack Applications

```bash
./scripts/find-icons.sh plex        # Returns: simple-icons:plex
./scripts/find-icons.sh sonarr      # Returns: simple-icons:sonarr
./scripts/find-icons.sh radarr      # Returns: simple-icons:radarr
./scripts/find-icons.sh jellyfin    # Returns: simple-icons:jellyfin
```

### Development Tools

```bash
./scripts/find-icons.sh git         # Returns: simple-icons:git
./scripts/find-icons.sh docker      # Returns: simple-icons:docker
./scripts/find-icons.sh kubernetes  # Returns: simple-icons:kubernetes
```

### Monitoring and Infrastructure

```bash
./scripts/find-icons.sh prometheus  # Returns: simple-icons:prometheus
./scripts/find-icons.sh grafana     # Returns: simple-icons:grafana
./scripts/find-icons.sh nginx       # Returns: simple-icons:nginx
```
