# Custom Error Pages Update Script

This script automatically updates the custom error pages for the OpenShift cluster from the [tarampampam/error-pages](https://github.com/tarampampam/error-pages) repository.

## Usage

### Using Task (Recommended)

```bash
# Update error pages
task update-error-pages

# Dry run to see what would be changed
task update-error-pages DRY_RUN=true
```

### Direct Script Usage

```bash
# Update error pages
python3 scripts/update-error-pages.py

# Dry run
python3 scripts/update-error-pages.py --dry-run
```

## What It Does

1. **Downloads** the latest error pages from `https://github.com/tarampampam/error-pages/zipball/gh-pages/`
2. **Extracts** all available error page templates
3. **Filters** templates that have both 404.html and 503.html files
4. **Converts** HTML files to HTTP response format required by OpenShift ingress
5. **Generates** Helm template files for each available template
6. **Updates** the `values.yaml` file with available template options
7. **Creates** comprehensive `README.md` with live preview links and template descriptions

## Available Templates

After running the script, you'll have templates for all available designs:

- `app-down` - Application maintenance page style
- `cats` - Cat-themed error pages
- `connection` - Network connection themed (default)
- `ghost` - Minimalist ghost theme
- `hacker-terminal` - Terminal/hacker aesthetic
- `l7` - Layer 7 network theme
- `lost-in-space` - Space-themed pages
- `noise` - Glitch/static effect theme
- `orient` - Eastern-inspired design
- `shuffle` - Playing card theme
- `win98` - Windows 98 nostalgic theme

## Switching Templates

To use a different template, update the `template` value in `charts/infrastructure/custom-error-pages/values.yaml`:

```yaml
custom-error-pages:
  template: cats # Change this to any available template
```

## File Structure

After running the script, you'll have:

```text
charts/infrastructure/custom-error-pages/
├── templates/
│   ├── app-down.yaml
│   ├── cats.yaml
│   ├── connection.yaml
│   ├── ghost.yaml
│   ├── hacker-terminal.yaml
│   ├── l7.yaml
│   ├── lost-in-space.yaml
│   ├── noise.yaml
│   ├── orient.yaml
│   ├── shuffle.yaml
│   └── win98.yaml
└── values.yaml (updated with template options)
```

Each template file contains both 404 and 503 error pages in the proper HTTP response format for OpenShift.

## Requirements

- Python 3.6+
- `requests` library (automatically available in the dev container)
- Internet connection to download error pages

## Notes

- Only error codes 404 and 503 are included (as requested)
- All templates are conditional based on the `template` value in `values.yaml`
- The script preserves any custom configuration in `values.yaml`
- HTML content is automatically converted to HTTP response format for OpenShift ingress compatibility
