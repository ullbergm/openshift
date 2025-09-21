#!/usr/bin/env python3
"""
Update Custom Error Pages Script

This script downloads the latest custom error pages from tarampampam/error-pages
and generates Helm templates for each available template with 404 and 503 error pages.

The script automatically strips all non-English localization data to reduce file size
while preserving the visual design and functionality of the error pages.
"""

import os
import sys
import zipfile
import requests
import tempfile
import shutil
from pathlib import Path
import argparse

def download_error_pages(temp_dir):
    """Download and extract the error-pages repository."""
    url = "https://github.com/tarampampam/error-pages/zipball/gh-pages/"
    print(f"Downloading error pages from {url}")

    response = requests.get(url, stream=True)
    response.raise_for_status()

    zip_path = temp_dir / "error-pages.zip"
    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Downloaded {zip_path.stat().st_size} bytes")

    # Extract the zip file
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    # Find the extracted directory (it has a random suffix)
    extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir() and d.name.startswith("tarampampam-error-pages-")]
    if not extracted_dirs:
        raise ValueError("Could not find extracted error-pages directory")

    return extracted_dirs[0]

def html_to_http_response(html_content, status_code, status_text):
    """Convert HTML content to HTTP response format."""
    http_response = f"""HTTP/1.0 {status_code} {status_text}
Cache-Control: no-cache
Connection: close
Content-Type: text/html

{html_content}"""
    return http_response

def strip_non_english_localization(html_content):
    """Remove all non-English localization data and clean up HTML to reduce file size."""
    import re

    # Remove the entire localization script block
    # This removes the entire <script> block that contains the l10n object
    l10n_script_pattern = r'<script>// // the very first line should be kept.*?Object\.defineProperty\(window, \'l10n\'.*?</script>'
    html_content = re.sub(l10n_script_pattern, '', html_content, flags=re.DOTALL)

    # Also remove any remaining l10n references
    l10n_call_pattern = r'window\.l10n\.localizeDocument\(\);'
    html_content = re.sub(l10n_call_pattern, '', html_content)

    # Remove all data-l10n attributes since we don't need them for English-only
    html_content = re.sub(r'\s*data-l10n(?:="[^"]*")?', '', html_content)

    # Remove empty HTML comments
    html_content = re.sub(r'<!--\s*-->', '', html_content)

    # Remove empty CSS comments
    html_content = re.sub(r'/\*\s*\*/', '', html_content)

    # Clean up trailing whitespace on lines
    html_content = re.sub(r'[ \t]+$', '', html_content, flags=re.MULTILINE)

    # Remove all empty lines (including lines with only whitespace) - apply multiple times to catch all
    while re.search(r'\n\s*\n', html_content):
        html_content = re.sub(r'\n\s*\n', '\n', html_content)

    return html_content

def get_available_templates(error_pages_dir):
    """Get list of available error page templates."""
    templates = []
    for item in error_pages_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Check if it has 404.html and 503.html
            has_404 = (item / "404.html").exists()
            has_503 = (item / "503.html").exists()
            if has_404 and has_503:
                templates.append(item.name)
    return sorted(templates)

def generate_template_file(template_name, error_pages_dir, output_dir):
    """Generate a Helm template file for a specific error page template."""
    import re
    template_dir = error_pages_dir / template_name

    # Read 404 and 503 HTML files
    html_404 = (template_dir / "404.html").read_text(encoding="utf-8")
    html_503 = (template_dir / "503.html").read_text(encoding="utf-8")

    # Strip non-English localization data to reduce file size significantly
    # This removes the large JavaScript l10n object and data-l10n attributes
    html_404 = strip_non_english_localization(html_404)
    html_503 = strip_non_english_localization(html_503)

    # Convert to HTTP response format
    http_404 = html_to_http_response(html_404, "404", "File Not Found")
    http_503 = html_to_http_response(html_503, "503", "Service Unavailable")

    # Generate Helm template content
    template_content = f'''{{{{- if eq (index .Values "custom-error-pages" "template") "{template_name}" }}}}
---
apiVersion: v1
kind: ConfigMap
metadata:
  labels:
    app.kubernetes.io/instance: custom-error-code-pages
  name: custom-error-code-pages
  namespace: openshift-config
data:
  error-page-404.http: |
{_indent_content(http_404, 4)}
  error-page-503.http: |
{_indent_content(http_503, 4)}
{{{{- end }}}}
'''

    # Strip spaces for empty lines in the template content
    template_content = re.sub(r'^\s+$', '', template_content, flags=re.MULTILINE)

    # Write template file
    output_file = output_dir / f"{template_name}.yaml"
    output_file.write_text(template_content, encoding="utf-8")
    print(f"Generated {output_file}")

def _indent_content(content, spaces):
    """Indent content by specified number of spaces."""
    indent = " " * spaces
    return "\n".join(indent + line for line in content.split("\n"))

def update_values_yaml(templates, values_file):
    """Update values.yaml with available templates."""
    if not values_file.exists():
        print(f"Warning: {values_file} does not exist")
        return

    content = values_file.read_text(encoding="utf-8")

    # Find the custom-error-pages section and update template options
    lines = content.split("\n")
    updated_lines = []
    in_custom_error_pages = False
    found_template_line = False
    added_comment = False

    for line in lines:
        if line.strip().startswith("custom-error-pages:"):
            in_custom_error_pages = True
            updated_lines.append(line)
        elif in_custom_error_pages and line.strip().startswith("# Available templates:"):
            # Update existing comment instead of adding a new one
            updated_lines.append(f"  # Available templates: {', '.join(templates)}")
            added_comment = True
        elif in_custom_error_pages and line.strip().startswith("template:"):
            found_template_line = True
            # Add comment if we haven't added it yet
            if not added_comment:
                updated_lines.append(f"  # Available templates: {', '.join(templates)}")
                added_comment = True
            # Keep existing template selection
            updated_lines.append(line)
            in_custom_error_pages = False
        else:
            updated_lines.append(line)

    if not found_template_line:
        print("Warning: Could not find template configuration in values.yaml")

    values_file.write_text("\n".join(updated_lines), encoding="utf-8")
    print(f"Updated {values_file} with available templates")

def generate_chart_readme(templates, chart_dir):
    """Generate comprehensive README.md for the chart with sample images."""
    readme_content = f"""# Custom Error Pages

A Helm chart for configuring custom error pages in OpenShift clusters using beautiful, modern designs from [tarampampam/error-pages](https://github.com/tarampampam/error-pages).

## Overview

This chart deploys custom 404 and 503 error pages that replace the default OpenShift/nginx error pages. The error pages are served as ConfigMaps in HTTP response format, compatible with OpenShift ingress controllers.

## Source

Error pages are automatically updated from: [https://github.com/tarampampam/error-pages](https://github.com/tarampampam/error-pages)

Live demos available at: [https://tarampampam.github.io/error-pages/](https://tarampampam.github.io/error-pages/)

## Available Templates

The chart includes {len(templates)} different error page templates, each with unique visual designs:

"""

    # Template descriptions for better documentation
    template_descriptions = {
        "app-down": "Application maintenance page style with a clean, professional look",
        "cats": "Cat-themed error pages (fetches cat images from external servers)",
        "connection": "Network connection themed with technical diagnostic styling",
        "ghost": "Minimalist ghost theme with subtle animations",
        "hacker-terminal": "Terminal/hacker aesthetic with green text on black background",
        "l7": "Layer 7 network theme with modern tech styling",
        "lost-in-space": "Space-themed pages with cosmic backgrounds and animations",
        "noise": "Glitch/static effect theme with digital distortion",
        "orient": "Eastern-inspired design with elegant typography",
        "shuffle": "Playing card theme with colorful, playful design",
        "win98": "Windows 98 nostalgic theme with classic dialog boxes"
    }

    for template in templates:
        description = template_descriptions.get(template, "Modern error page design")
        readme_content += f"""### {template}

{description}

- **404 Preview**: [https://tarampampam.github.io/error-pages/{template}/404.html](https://tarampampam.github.io/error-pages/{template}/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/{template}/503.html](https://tarampampam.github.io/error-pages/{template}/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

"""

    readme_content += f"""## Installation

### Prerequisites

- OpenShift 4.x cluster
- Helm 3.x
- Cluster admin access to create ConfigMaps in `openshift-config` namespace

### Deploy the Chart

```bash
# Add the chart repository (if using a Helm repository)
helm repo add your-repo https://your-chart-repository.com

# Install with default template (connection)
helm install custom-error-pages ./charts/infrastructure/custom-error-pages

# Install with a specific template
helm install custom-error-pages ./charts/infrastructure/custom-error-pages \\
  --set custom-error-pages.template=cats
```

## Configuration

### Available Templates

Update the template in your `values.yaml`:

```yaml
custom-error-pages:
  # Available templates: {', '.join(templates)}
  template: connection  # Change to any available template
```

### Switching Templates

To change the error page design:

1. Update the `template` value in your `values.yaml`
2. Apply the changes:
   ```bash
   helm upgrade custom-error-pages ./charts/infrastructure/custom-error-pages
   ```

### Template Options

| Template | Description | Preview Links |
|----------|-------------|---------------|"""

    for template in templates:
        description = template_descriptions.get(template, "Modern design")
        readme_content += f"""
| `{template}` | {description} | [404](https://tarampampam.github.io/error-pages/{template}/404.html) \\| [503](https://tarampampam.github.io/error-pages/{template}/503.html) |"""

    readme_content += f"""

## How It Works

1. **ConfigMap Creation**: The chart creates a ConfigMap named `custom-error-code-pages` in the `openshift-config` namespace
2. **HTTP Response Format**: Error pages are stored in HTTP response format, ready for OpenShift ingress controllers
3. **Template Selection**: Only the selected template is deployed, keeping the ConfigMap size minimal
4. **Error Codes**: Includes both 404 (Not Found) and 503 (Service Unavailable) error pages

## Updating Error Pages

To get the latest error page designs from upstream:

```bash
# Update using the provided task
task update-error-pages

# Or run the script directly
python3 scripts/update-error-pages.py
```

This will:
- Download the latest templates from [tarampampam/error-pages](https://github.com/tarampampam/error-pages)
- Update all template files
- Refresh this README with current template information

## Template Structure

Each template generates a Helm template file with the following structure:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: custom-error-code-pages
  namespace: openshift-config
data:
  error-page-404.http: |
    HTTP/1.0 404 File Not Found
    Cache-Control: no-cache
    Connection: close
    Content-Type: text/html

    <!DOCTYPE html>
    <!-- Error page HTML content -->
  error-page-503.http: |
    HTTP/1.0 503 Service Unavailable
    Cache-Control: no-cache
    Connection: close
    Content-Type: text/html

    <!DOCTYPE html>
    <!-- Error page HTML content -->
```

## OpenShift Integration

These error pages integrate with OpenShift's ingress controllers. The ConfigMap must be in the `openshift-config` namespace to be recognized by the OpenShift router.

## Troubleshooting

### Error Pages Not Showing

1. Verify the ConfigMap exists:
   ```bash
   oc get configmap custom-error-code-pages -n openshift-config
   ```

2. Check the OpenShift router configuration:
   ```bash
   oc get ingresscontroller default -n openshift-ingress-operator -o yaml
   ```

3. Ensure the template name is valid:
   ```bash
   # List available templates
   helm template ./charts/infrastructure/custom-error-pages --show-only templates/
   ```

### Template Not Found

If you get a template not found error, ensure the template name matches exactly one of the available templates: {', '.join(templates)}

## Contributing

To add new templates or update existing ones:

1. Run the update script: `task update-error-pages`
2. Test the new templates with different error codes
3. Update documentation as needed

## License

This chart uses error pages from [tarampampam/error-pages](https://github.com/tarampampam/error-pages) which is licensed under the MIT License.

---

*Last updated: Generated automatically by `scripts/update-error-pages.py`*
"""

    readme_file = chart_dir / "README.md"
    readme_file.write_text(readme_content, encoding="utf-8")
    print(f"Generated comprehensive README at {readme_file}")

    return readme_file

def main():
    parser = argparse.ArgumentParser(description="Update custom error pages from tarampampam/error-pages")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    chart_dir = repo_root / "charts" / "infrastructure" / "custom-error-pages"
    templates_dir = chart_dir / "templates"
    values_file = chart_dir / "values.yaml"

    if not chart_dir.exists():
        print(f"Error: Chart directory {chart_dir} does not exist")
        sys.exit(1)

    print(f"Updating error pages for chart at {chart_dir}")

    if args.dry_run:
        print("DRY RUN: No files will be modified")

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Download and extract error pages
            error_pages_dir = download_error_pages(temp_path)
            print(f"Extracted to {error_pages_dir}")

            # Get available templates
            templates = get_available_templates(error_pages_dir)
            print(f"Found {len(templates)} templates: {', '.join(templates)}")

            if not templates:
                print("Error: No templates found with both 404.html and 503.html")
                sys.exit(1)

            if not args.dry_run:
                # Remove existing template files (except any custom ones)
                if templates_dir.exists():
                    for template_file in templates_dir.glob("*.yaml"):
                        if template_file.stem in templates or template_file.stem == "connection":
                            print(f"Removing old template {template_file}")
                            template_file.unlink()
                else:
                    templates_dir.mkdir(parents=True)

                # Generate new template files
                for template_name in templates:
                    generate_template_file(template_name, error_pages_dir, templates_dir)

                # Update values.yaml with available templates
                update_values_yaml(templates, values_file)

                # Generate comprehensive README.md
                generate_chart_readme(templates, chart_dir)

                print(f"\nSuccessfully updated {len(templates)} error page templates")
                print("Available templates:")
                for template in templates:
                    print(f"  - {template}")
                print(f"\nTo use a different template, update the 'template' value in {values_file}")
                print(f"Comprehensive documentation available in {chart_dir / 'README.md'}")
            else:
                print(f"\nWould generate {len(templates)} template files:")
                for template in templates:
                    print(f"  - {templates_dir}/{template}.yaml")
                print(f"Would update {values_file} with template options")
                print(f"Would generate comprehensive README at {chart_dir / 'README.md'}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
