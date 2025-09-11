# Icon Validation

The Helm validation suite now includes comprehensive icon validation to ensure consistency and proper formatting of icons across all applications. This includes validation for both Iconify icons and HTTP URL-based icons.

## Icon Formats Supported

### Plain Icons (Default to MDI)

Plain icon names without a collection prefix default to MDI (Material Design Icons):

```yaml
icon: robot        # Equivalent to mdi:robot
icon: book-open    # Equivalent to mdi:book-open
icon: music-box    # Equivalent to mdi:music-box
```

### Collection-Prefixed Icons

Any Iconify collection can be specified with the `collection:` prefix:

```yaml
# Material Design Icons (explicit)
icon: mdi:draw-pen
icon: mdi:book-open-page-variant

# Simple Icons (brand icons)
icon: simple-icons:youtube
icon: simple-icons:radarr

# Lucide Icons
icon: lucide:pen-tool
icon: lucide:heart

# Any other Iconify collection
icon: tabler:device-desktop
icon: heroicons:academic-cap
```

### HTTP URL Icons

Direct HTTP/HTTPS URLs to icon images are also supported and validated:

```yaml
# GitHub raw images
image: "https://raw.githubusercontent.com/Radarr/Radarr/develop/Logo/256.png"

# Application favicons
image: "https://ollama.ai/public/apple-touch-icon.png"

# Custom hosted images
image: "https://avatars.githubusercontent.com/u/59452120"
```

## Validation Rules

### Format Validation (Always Performed)

1. **Generic Collections**: Most icon collections (mdi, lucide, tabler, heroicons, etc.) must contain only lowercase letters, numbers, and hyphens
2. **Simple Icons**: Must follow the format `simple-icons:iconname` with lowercase letters, numbers, hyphens, and dots only
3. **Collection Detection**: Icons with `collection:name` format are parsed automatically; icons without a prefix default to `mdi`
4. **HTTP URLs**: Must start with `http://` or `https://` and follow proper URL format
5. **Missing Icons**: The validator will suggest intelligent defaults using online API search when available
6. **Empty Icons**: Will trigger a warning with dynamically generated or fallback suggestions

### Online Validation (Optional)

When `--online` flag is used, the validator will also:

1. **Verify Iconify Icon Existence**: Check if icons actually exist in the Iconify database
2. **Collection Validation**: Verify that the icon collection (mdi, simple-icons) is available
3. **HTTP URL Accessibility**: Test HTTP/HTTPS URLs to ensure they return successful responses (200, 201, 202, 204)
4. **Dynamic Suggestions**: Search Simple Icons API for exact and partial matches when suggesting defaults
5. **Network Handling**: Gracefully handle network timeouts and API failures
6. **Caching**: Cache API responses to avoid repeated requests for the same icons and collections

### Validation Modes

- **Online Mode (Default)**: Format validation + Iconify database verification + URL accessibility testing + dynamic icon suggestions
- **Offline Mode**: Fast format validation with hardcoded fallback suggestions, no network requests## Running Icon Validation

### Online Validation (Default)

```bash
# Run icon validation with online verification (default)
task helm:validate-icons

# Run all helm validation with online icon verification (default)
task helm:validate-all

# Run complete validation suite with online verification (default)
task validate:all
```

### Offline Validation (Fast Mode)

```bash
# Run icon validation only (offline mode)
task helm:validate-icons-offline

# Run all helm validation (including icons, offline mode)
task helm:validate-all-offline

# Run complete validation suite (offline mode)
task validate:all-offline
```

### Manual Script Usage

```bash
# Offline validation
scripts/validate-icons.sh

# Online validation
scripts/validate-icons.sh --online

# Online validation with custom timeout
scripts/validate-icons.sh --online --timeout 10
```

## Default Icon Suggestions

The validator provides intelligent defaults based on:

- Application name patterns
- Application category (ai, media, utilities, etc.)

For example:

- AI/ML applications: `robot`, `brain`
- Media applications: Service-specific icons like `simple-icons:sonarr`
- Utilities: Context-appropriate icons like `mdi:draw-pen` for drawing apps

## Example Output

### Offline Validation

```text
🎨 Validating icons in Helm charts (offline mode)...
  ✅ ollama: Icon 'robot' format is valid
  ✅ ollama: Image URL 'https://ollama.ai/public/apple-touch-icon.png' format is valid
  ⚠️  metube: No icon field found, suggested: simple-icons:youtube
  ⚠️  metube (line 19): Image field is empty
  ❌ sonarr (line 17): Invalid simple-icons format. Should be 'simple-icons:iconname' with lowercase letters, numbers, hyphens, and dots only.

— Icon validation summary —
⚠️  Icon validation completed with warnings
    ℹ️  Use --online flag for Iconify database verification
```

### Online Validation

```text
🎨 Validating icons in Helm charts (online mode)...
🌐 Checking Iconify API connectivity... ✓
  ✅ ollama: Icon 'robot' is valid (verified online)
  ✅ ollama: Image URL 'https://ollama.ai/public/apple-touch-icon.png' is accessible (verified online)
  ❌ radarr (line 19): Image URL 'https://example.com/broken-image.png' returned HTTP error (404, 403, etc.)
  ⚠️  metube (line 17): Icon 'nonexistent-icon' not found in Iconify database
  ⚠️  sonarr: Icon 'timeout-test' format valid (online check failed - network error)

— Icon validation summary —
❌ Icon validation failed - fix the errors above
```

## Smart Icon Suggestions

The validation system includes intelligent icon suggestions for applications missing icon definitions:

### Online Suggestion Mode (Default with --online)

When online validation is enabled, the system:

1. **API Search**: Queries the Simple Icons API for exact matches with the application name
2. **Partial Matching**: Falls back to partial string matching if no exact match is found
3. **Collection Priority**: Prioritizes Simple Icons for brand/application icons, MDI for generic icons
4. **Caching**: Caches Simple Icons collection data to minimize API calls

```bash
# Examples of online suggestions
⚠️  metube: No icon field found, suggested: simple-icons:youtube
⚠️  plex: No icon field found, suggested: simple-icons:plex
⚠️  grafana: No icon field found, suggested: simple-icons:grafana
```

### Offline Suggestion Mode (Fallback)

When network is unavailable or API calls fail:

1. **Hardcoded Mapping**: Uses predefined application-to-icon mappings
2. **Category Defaults**: Falls back to category-based defaults (e.g., `play-circle` for media apps)
3. **Generic Fallback**: Provides `application` icon as last resort

```bash
# Examples of offline suggestions
⚠️  unknown-app: No icon field found, suggested: play-circle
⚠️  media-app: No icon field found, suggested: movie
```

## Dependencies

- `curl` - For making HTTP requests to Iconify API and validating HTTP URL accessibility
- `jq` - For parsing JSON responses from the API
