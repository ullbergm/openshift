# Custom Error Pages

A Helm chart for configuring custom error pages in OpenShift clusters using beautiful, modern designs from [tarampampam/error-pages](https://github.com/tarampampam/error-pages).

## Overview

This chart deploys custom 404 and 503 error pages that replace the default OpenShift/nginx error pages. The error pages are served as ConfigMaps in HTTP response format, compatible with OpenShift ingress controllers.

## Source

Error pages are automatically updated from: [https://github.com/tarampampam/error-pages](https://github.com/tarampampam/error-pages)

Live demos available at: [https://tarampampam.github.io/error-pages/](https://tarampampam.github.io/error-pages/)

## Available Templates

The chart includes 11 different error page templates, each with unique visual designs:

### app-down

Application maintenance page style with a clean, professional look

- **404 Preview**: [https://tarampampam.github.io/error-pages/app-down/404.html](https://tarampampam.github.io/error-pages/app-down/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/app-down/503.html](https://tarampampam.github.io/error-pages/app-down/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

### cats

Cat-themed error pages (fetches cat images from external servers)

- **404 Preview**: [https://tarampampam.github.io/error-pages/cats/404.html](https://tarampampam.github.io/error-pages/cats/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/cats/503.html](https://tarampampam.github.io/error-pages/cats/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

### connection

Network connection themed with technical diagnostic styling

- **404 Preview**: [https://tarampampam.github.io/error-pages/connection/404.html](https://tarampampam.github.io/error-pages/connection/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/connection/503.html](https://tarampampam.github.io/error-pages/connection/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

### ghost

Minimalist ghost theme with subtle animations

- **404 Preview**: [https://tarampampam.github.io/error-pages/ghost/404.html](https://tarampampam.github.io/error-pages/ghost/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/ghost/503.html](https://tarampampam.github.io/error-pages/ghost/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

### hacker-terminal

Terminal/hacker aesthetic with green text on black background

- **404 Preview**: [https://tarampampam.github.io/error-pages/hacker-terminal/404.html](https://tarampampam.github.io/error-pages/hacker-terminal/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/hacker-terminal/503.html](https://tarampampam.github.io/error-pages/hacker-terminal/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

### l7

Layer 7 network theme with modern tech styling

- **404 Preview**: [https://tarampampam.github.io/error-pages/l7/404.html](https://tarampampam.github.io/error-pages/l7/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/l7/503.html](https://tarampampam.github.io/error-pages/l7/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

### lost-in-space

Space-themed pages with cosmic backgrounds and animations

- **404 Preview**: [https://tarampampam.github.io/error-pages/lost-in-space/404.html](https://tarampampam.github.io/error-pages/lost-in-space/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/lost-in-space/503.html](https://tarampampam.github.io/error-pages/lost-in-space/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

### noise

Glitch/static effect theme with digital distortion

- **404 Preview**: [https://tarampampam.github.io/error-pages/noise/404.html](https://tarampampam.github.io/error-pages/noise/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/noise/503.html](https://tarampampam.github.io/error-pages/noise/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

### orient

Eastern-inspired design with elegant typography

- **404 Preview**: [https://tarampampam.github.io/error-pages/orient/404.html](https://tarampampam.github.io/error-pages/orient/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/orient/503.html](https://tarampampam.github.io/error-pages/orient/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

### shuffle

Playing card theme with colorful, playful design

- **404 Preview**: [https://tarampampam.github.io/error-pages/shuffle/404.html](https://tarampampam.github.io/error-pages/shuffle/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/shuffle/503.html](https://tarampampam.github.io/error-pages/shuffle/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

### win98

Windows 98 nostalgic theme with classic dialog boxes

- **404 Preview**: [https://tarampampam.github.io/error-pages/win98/404.html](https://tarampampam.github.io/error-pages/win98/404.html)
- **503 Preview**: [https://tarampampam.github.io/error-pages/win98/503.html](https://tarampampam.github.io/error-pages/win98/503.html)

> **Live Preview**: Open the links above to see the actual error pages in your browser.

## Installation

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
helm install custom-error-pages ./charts/infrastructure/custom-error-pages \
  --set custom-error-pages.template=cats
```

## Configuration

### Available Templates

Update the template in your `values.yaml`:

```yaml
custom-error-pages:
  # Available templates: app-down, cats, connection, ghost, hacker-terminal, l7, lost-in-space, noise, orient, shuffle, win98
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
|----------|-------------|---------------|
| `app-down` | Application maintenance page style with a clean, professional look | [404](https://tarampampam.github.io/error-pages/app-down/404.html) \| [503](https://tarampampam.github.io/error-pages/app-down/503.html) |
| `cats` | Cat-themed error pages (fetches cat images from external servers) | [404](https://tarampampam.github.io/error-pages/cats/404.html) \| [503](https://tarampampam.github.io/error-pages/cats/503.html) |
| `connection` | Network connection themed with technical diagnostic styling | [404](https://tarampampam.github.io/error-pages/connection/404.html) \| [503](https://tarampampam.github.io/error-pages/connection/503.html) |
| `ghost` | Minimalist ghost theme with subtle animations | [404](https://tarampampam.github.io/error-pages/ghost/404.html) \| [503](https://tarampampam.github.io/error-pages/ghost/503.html) |
| `hacker-terminal` | Terminal/hacker aesthetic with green text on black background | [404](https://tarampampam.github.io/error-pages/hacker-terminal/404.html) \| [503](https://tarampampam.github.io/error-pages/hacker-terminal/503.html) |
| `l7` | Layer 7 network theme with modern tech styling | [404](https://tarampampam.github.io/error-pages/l7/404.html) \| [503](https://tarampampam.github.io/error-pages/l7/503.html) |
| `lost-in-space` | Space-themed pages with cosmic backgrounds and animations | [404](https://tarampampam.github.io/error-pages/lost-in-space/404.html) \| [503](https://tarampampam.github.io/error-pages/lost-in-space/503.html) |
| `noise` | Glitch/static effect theme with digital distortion | [404](https://tarampampam.github.io/error-pages/noise/404.html) \| [503](https://tarampampam.github.io/error-pages/noise/503.html) |
| `orient` | Eastern-inspired design with elegant typography | [404](https://tarampampam.github.io/error-pages/orient/404.html) \| [503](https://tarampampam.github.io/error-pages/orient/503.html) |
| `shuffle` | Playing card theme with colorful, playful design | [404](https://tarampampam.github.io/error-pages/shuffle/404.html) \| [503](https://tarampampam.github.io/error-pages/shuffle/503.html) |
| `win98` | Windows 98 nostalgic theme with classic dialog boxes | [404](https://tarampampam.github.io/error-pages/win98/404.html) \| [503](https://tarampampam.github.io/error-pages/win98/503.html) |

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

If you get a template not found error, ensure the template name matches exactly one of the available templates: app-down, cats, connection, ghost, hacker-terminal, l7, lost-in-space, noise, orient, shuffle, win98

## Contributing

To add new templates or update existing ones:

1. Run the update script: `task update-error-pages`
2. Test the new templates with different error codes
3. Update documentation as needed

## License

This chart uses error pages from [tarampampam/error-pages](https://github.com/tarampampam/error-pages) which is licensed under the MIT License.

---

*Last updated: Generated automatically by `scripts/update-error-pages.py`*
