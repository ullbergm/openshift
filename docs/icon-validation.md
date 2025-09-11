# Icon Validation

The Helm validation suite now includes icon validation to ensure consistency and proper formatting of icons across all applications.

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

## Validation Rules

### Format Validation (Always Performed)

1. **Generic Collections**: Most icon collections (mdi, lucide, tabler, heroicons, etc.) must contain only lowercase letters, numbers, and hyphens
2. **Simple Icons**: Must follow the format `simple-icons:iconname` with lowercase letters, numbers, hyphens, and dots only
3. **Collection Detection**: Icons with `collection:name` format are parsed automatically; icons without a prefix default to `mdi`
4. **Missing Icons**: The validator will suggest intelligent defaults using online API search when available
5. **Empty Icons**: Will trigger a warning with dynamically generated or fallback suggestions

### Online Validation (Optional)

When `--online` flag is used, the validator will also:

1. **Verify Icon Existence**: Check if icons actually exist in the Iconify database
2. **Collection Validation**: Verify that the icon collection (mdi, simple-icons) is available
3. **Dynamic Suggestions**: Search Simple Icons API for exact and partial matches when suggesting defaults
4. **Network Handling**: Gracefully handle network timeouts and API failures
5. **Caching**: Cache API responses to avoid repeated requests for the same icons and collections

### Validation Modes

- **Offline Mode**: Fast format validation with hardcoded fallback suggestions, no network requests
- **Online Mode**: Format validation + Iconify database verification + dynamic icon suggestions

## Running Icon Validation

### Offline Validation (Default)

```bash
# Run icon validation only (offline)
task helm:validate-icons

# Run all helm validation (including icons, offline)
task helm:validate-all

# Run complete validation suite (offline)
task validate:all
```

### Online Validation (Iconify Database Verification)

```bash
# Run icon validation with online verification
task helm:validate-icons-online

# Run all helm validation with online icon verification
task helm:validate-all-online

# Run complete validation suite with online verification
task validate:all-online
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
  ✅ ollama: Icon 'robot' is valid
  ⚠️  metube: No icon field found, suggested: simple-icons:youtube
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
  ❌ metube (line 17): Icon 'nonexistent-icon' not found in Iconify database
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

- `curl` - For making HTTP requests to Iconify API
- `jq` - For parsing JSON responses from the API
