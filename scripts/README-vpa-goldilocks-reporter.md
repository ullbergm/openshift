# VPA Goldilocks Reporter

A comprehensive Python script that reads VPA (Vertical Pod Autoscaler) recommendations from Goldilocks and generates detailed reports for recommended resource configuration in Kubernetes clusters.

## Features

- 🔍 **Multi-format Reports**: Generate reports in console, JSON, YAML, HTML, and kubectl patch formats
- 📊 **Comprehensive Analysis**: Compares current resource configurations with VPA recommendations
- 🎯 **Namespace Filtering**: Analyze specific namespaces or all namespaces
- 🚀 **Rich Console Output**: Beautiful, color-coded console reports using Rich library
- 📝 **HTML Reports**: Professional HTML reports with charts and styling
- ⚡ **kubectl Integration**: Generate ready-to-use kubectl patch commands
- 🔧 **Flexible Configuration**: Support for custom kubeconfig files

## Prerequisites

- Python 3.7+
- Kubernetes cluster with VPA and Goldilocks installed
- kubectl configured to access your cluster
- Required Python packages (see requirements.txt)

## Installation

1. Install the required dependencies:

```bash
pip install -r scripts/requirements.txt
```

2. Make sure you have access to a Kubernetes cluster with VPA enabled and Goldilocks deployed.

## Usage

### Basic Console Report

```bash
./scripts/vpa-goldilocks-reporter.py
```

### Generate JSON Report

```bash
./scripts/vpa-goldilocks-reporter.py --format json --output vpa-report.json
```

### Generate HTML Report for Specific Namespace

```bash
./scripts/vpa-goldilocks-reporter.py --format html --output media-vpa-report.html --namespace media
```

### Generate kubectl Patch Commands

```bash
./scripts/vpa-goldilocks-reporter.py --format kubectl --output apply-recommendations.sh
```

### Using Custom kubeconfig

```bash
./scripts/vpa-goldilocks-reporter.py --kubeconfig ~/.kube/my-cluster-config --format yaml --output recommendations.yaml
```

### Verbose Output

```bash
./scripts/vpa-goldilocks-reporter.py --verbose --format console
```

## Output Formats

### Console Format (Default)

- Rich, color-coded tables displayed in terminal
- Summary overview and detailed per-container recommendations
- Real-time progress indicators

### JSON Format

```json
{
  "metadata": {
    "generatedAt": "2025-09-12T10:30:00.000000",
    "totalVPAs": 5,
    "generator": "vpa-goldilocks-reporter"
  },
  "vpas": [
    {
      "name": "plex-vpa",
      "namespace": "media",
      "target": {
        "kind": "Deployment",
        "name": "plex"
      },
      "recommendations": {
        "plex": {
          "target": {
            "cpu": "100m",
            "memory": "256Mi"
          }
        }
      }
    }
  ]
}
```

### Markdown Format

- Clean, readable documentation-style report
- Well-formatted tables and professional structure
- Git-friendly and suitable for sharing with teams

### YAML Format

- Structured YAML output
- Easy to parse and integrate with other tools
- Git-friendly for version control

### kubectl Format

- Ready-to-execute kubectl patch commands
- Applies VPA target recommendations directly
- Includes safety comments with context

## Command Line Options

| Option         | Description                                           | Default            |
| -------------- | ----------------------------------------------------- | ------------------ |
| `--format`     | Output format: console, json, yaml, markdown, kubectl | console            |
| `--output`     | Output file path (required for non-console formats)   | -                  |
| `--namespace`  | Specific namespace to analyze                         | All namespaces     |
| `--kubeconfig` | Path to kubeconfig file                               | Default kubeconfig |
| `--verbose`    | Enable verbose logging                                | False              |

## Report Contents

The script provides comprehensive information about VPA recommendations:

### Summary Information

- Total number of VPAs in the cluster
- VPAs with active recommendations
- Generation timestamp

### Per-VPA Details

- **VPA Metadata**: Name, namespace, target workload
- **Update Mode**: Off, Auto, or Recreate
- **Current Resources**: Existing CPU and memory requests/limits
- **Recommendations**: Lower bound, target, and upper bound values
- **Container Analysis**: Per-container resource recommendations

### Resource Metrics

- **CPU**: Measured in cores (e.g., 100m, 1.5)
- **Memory**: Measured in bytes with units (e.g., 256Mi, 1Gi)
- **Comparison**: Current vs. recommended values

## Integration Examples

### CI/CD Pipeline Integration

```bash
# Generate report and fail if recommendations differ significantly
./scripts/vpa-goldilocks-reporter.py --format json --output current-recommendations.json
# Add logic to compare with baseline and alert on significant changes
```

### Monitoring and Alerting

```bash
# Generate daily reports for resource planning
./scripts/vpa-goldilocks-reporter.py --format html --output "reports/vpa-$(date +%Y%m%d).html"
```

### Automated Resource Updates

```bash
# Generate and review kubectl patches
./scripts/vpa-goldilocks-reporter.py --format kubectl --output patches.sh
# Review patches before applying
cat patches.sh
# Apply patches (after review)
bash patches.sh
```

## Troubleshooting

### Common Issues

1. **No VPA recommendations found**

   - Ensure VPA is installed and running in your cluster
   - Check that Goldilocks is deployed and monitoring your namespaces
   - Verify that workloads have been running long enough to generate recommendations

2. **Kubernetes connection errors**

   - Verify kubeconfig is valid: `kubectl cluster-info`
   - Check if you have proper RBAC permissions to list VPAs
   - Ensure the VPA CRDs are installed: `kubectl get crd | grep verticalpodautoscalers`

3. **Permission errors**
   - The script requires read access to VPAs, pods, deployments, statefulsets, and daemonsets
   - Ensure your service account has the necessary ClusterRole bindings

### Required RBAC Permissions

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: vpa-reporter
rules:
  - apiGroups: [""]
    resources: ["namespaces", "pods"]
    verbs: ["list", "get"]
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets", "daemonsets"]
    verbs: ["list", "get"]
  - apiGroups: ["autoscaling.k8s.io"]
    resources: ["verticalpodautoscalers"]
    verbs: ["list", "get"]
```

## Development

### Testing the Script

```bash
# Test with dry-run (console output only)
./scripts/vpa-goldilocks-reporter.py --verbose

# Test specific namespace
./scripts/vpa-goldilocks-reporter.py --namespace kube-system

# Generate test reports
./scripts/vpa-goldilocks-reporter.py --format json --output test-report.json
```

### Adding New Features

The script is designed to be extensible. Key areas for enhancement:

- Additional output formats (CSV, Prometheus metrics)
- Resource efficiency calculations
- Historical trend analysis
- Integration with external monitoring systems

## Contributing

1. Follow existing code style and patterns
2. Add appropriate error handling and logging
3. Update this README with any new features
4. Test with various Kubernetes configurations

## License

This script is part of the OpenShift cluster management tools and follows the same licensing as the parent project.
