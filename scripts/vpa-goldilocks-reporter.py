#!/usr/bin/env python3
"""
VPA Goldilocks Resource Recommendation Reporter

This script reads VPA (Vertical Pod Autoscaler) recommendations from Goldilocks
and generates comprehensive reports for recommended resource configuration.

Usage:
    python vpa-goldilocks-reporter.py --help
    python vpa-goldilocks-reporter.py --format json --output report.json
    python vpa-goldilocks-reporter.py --format html --output report.html --namespace media
"""

import argparse
import json
import logging
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

# Suppress SSL warnings for self-signed certificates
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
except ImportError:
    print("Error: kubernetes package not found. Install with: pip install kubernetes")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import track
    from rich import print as rprint
except ImportError:
    print("Error: rich package not found. Install with: pip install rich")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VPARecommendationReporter:
    """Main class for generating VPA resource recommendation reports."""

    def __init__(self, kubeconfig_path: Optional[str] = None, insecure: bool = False):
        """Initialize the reporter with Kubernetes configuration."""
        self.console = Console()
        self.k8s_client = None
        self.custom_objects_api = None

        # Load Kubernetes configuration
        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config()

            # Configure SSL verification if needed
            if insecure:
                # Disable SSL verification for self-signed certificates
                configuration = client.Configuration.get_default_copy()
                configuration.verify_ssl = False
                configuration.ssl_ca_cert = None
                client.Configuration.set_default(configuration)

            self.k8s_client = client.ApiClient()
            self.custom_objects_api = client.CustomObjectsApi()
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()

            logger.info("Successfully connected to Kubernetes cluster")
        except Exception as e:
            logger.error(f"Failed to connect to Kubernetes: {e}")
            raise

    @staticmethod
    def format_resource_value(value: str, resource_type: str) -> str:
        """Format resource values to standard Kubernetes formats."""
        if value in ['N/A', '', None]:
            return value

        if resource_type.lower() == 'cpu':
            # CPU formatting - convert to millicores if needed
            if value.endswith('m'):
                try:
                    cpu_val = int(value[:-1])
                    if cpu_val < 50:
                        return "25m"  # Minimum practical CPU
                    elif cpu_val < 100:
                        return "50m"
                    elif cpu_val < 250:
                        return "100m"
                    elif cpu_val < 500:
                        return "250m"
                    elif cpu_val < 1000:
                        return "500m"
                    else:
                        return f"{cpu_val // 1000}"  # Convert to full cores
                except ValueError:
                    return value
            elif '.' in value:
                # Handle decimal cores (e.g., "0.1" -> "100m")
                try:
                    cpu_float = float(value)
                    if cpu_float < 0.025:
                        return "25m"
                    elif cpu_float < 0.05:
                        return "25m"
                    elif cpu_float < 0.1:
                        return "50m"
                    elif cpu_float < 0.25:
                        return "100m"
                    elif cpu_float < 0.5:
                        return "250m"
                    elif cpu_float < 1:
                        return "500m"
                    else:
                        return str(int(cpu_float))
                except ValueError:
                    return value
            return value

        elif resource_type.lower() == 'memory':
            # Memory formatting - convert to standard units
            try:
                # Handle various memory formats
                if value.endswith('k') or value.endswith('K'):
                    # Convert from kilobytes
                    mem_kb = int(value[:-1])
                    if mem_kb < 512:  # Less than 512KB -> 256Mi
                        return "256Mi"
                    elif mem_kb < 1024:  # Less than 1MB -> 512Mi
                        return "512Mi"
                    else:
                        # Convert KB to MB then round
                        mem_mb = mem_kb / 1024
                        return VPARecommendationReporter._round_memory_mb(mem_mb)

                elif value.endswith('M') or value.endswith('Mi'):
                    # Already in MB/MiB - just round
                    mem_val = int(value.replace('Mi', '').replace('M', ''))
                    return VPARecommendationReporter._round_memory_mb(mem_val)

                elif value.endswith('G') or value.endswith('Gi'):
                    # Convert from GB/GiB to MB then round
                    mem_gb = float(value.replace('Gi', '').replace('G', ''))
                    mem_mb = mem_gb * 1024
                    return VPARecommendationReporter._round_memory_mb(mem_mb)

                elif value.isdigit():
                    # Raw bytes - convert to MB then round
                    mem_bytes = int(value)
                    mem_mb = mem_bytes / (1024 * 1024)
                    return VPARecommendationReporter._round_memory_mb(mem_mb)

                else:
                    return value

            except (ValueError, TypeError):
                return value

        return value

    @staticmethod
    def _round_memory_mb(mem_mb: float) -> str:
        """Round memory in MB to standard Kubernetes values."""
        if mem_mb < 128:
            return "128Mi"
        elif mem_mb < 256:
            return "256Mi"
        elif mem_mb < 512:
            return "512Mi"
        elif mem_mb < 1024:
            return f"{int((mem_mb + 127) // 128 * 128)}Mi"  # Round to nearest 128Mi
        else:
            # Convert to Gi for values >= 1GB
            mem_gb = mem_mb / 1024
            if mem_gb < 2:
                return "1Gi"
            elif mem_gb < 4:
                return "2Gi"
            elif mem_gb < 8:
                return "4Gi"
            elif mem_gb < 16:
                return "8Gi"
            else:
                return f"{int((mem_gb + 1) // 2 * 2)}Gi"  # Round to nearest 2Gi

    def get_vpa_recommendations(self, namespace: Optional[str] = None) -> List[Dict]:
        """Fetch VPA recommendations from the cluster."""
        vpas = []

        try:
            if namespace:
                namespaces = [namespace]
            else:
                # Get all namespaces
                ns_response = self.core_v1.list_namespace()
                namespaces = [ns.metadata.name for ns in ns_response.items]

            for ns in track(namespaces, description="Fetching VPA recommendations..."):
                try:
                    vpa_response = self.custom_objects_api.list_namespaced_custom_object(
                        group="autoscaling.k8s.io",
                        version="v1",
                        namespace=ns,
                        plural="verticalpodautoscalers"
                    )

                    for vpa in vpa_response.get('items', []):
                        vpas.append(self._process_vpa(vpa, ns))

                except ApiException as e:
                    if e.status != 404:  # Ignore namespaces without VPAs
                        logger.warning(f"Could not fetch VPAs from namespace {ns}: {e}")

        except Exception as e:
            logger.error(f"Error fetching VPA recommendations: {e}")
            raise

        return vpas

    def _process_vpa(self, vpa: Dict, namespace: str) -> Dict:
        """Process a single VPA object and extract relevant information."""
        metadata = vpa.get('metadata', {})
        spec = vpa.get('spec', {})
        status = vpa.get('status', {})

        # Get target reference information
        target_ref = spec.get('targetRef', {})

        # Extract recommendations
        recommendations = {}
        if 'recommendation' in status:
            recommendation = status['recommendation']
            container_recommendations = recommendation.get('containerRecommendations', [])

            for container_rec in container_recommendations:
                container_name = container_rec.get('containerName')

                recommendations[container_name] = {
                    'lowerBound': container_rec.get('lowerBound', {}),
                    'target': container_rec.get('target', {}),
                    'upperBound': container_rec.get('upperBound', {}),
                    'uncappedTarget': container_rec.get('uncappedTarget', {})
                }

        # Get current resource configuration if available
        current_resources = self._get_current_resources(
            namespace,
            target_ref.get('kind'),
            target_ref.get('name')
        )

        return {
            'name': metadata.get('name'),
            'namespace': namespace,
            'target': {
                'kind': target_ref.get('kind'),
                'name': target_ref.get('name'),
                'apiVersion': target_ref.get('apiVersion')
            },
            'updateMode': spec.get('updatePolicy', {}).get('updateMode', 'Off'),
            'recommendations': recommendations,
            'currentResources': current_resources,
            'lastUpdated': status.get('lastRecommendation'),
            'conditions': status.get('conditions', [])
        }

    def _get_current_resources(self, namespace: str, kind: str, name: str) -> Dict:
        """Get current resource configuration for the target workload."""
        try:
            if kind == 'Deployment':
                deployment = self.apps_v1.read_namespaced_deployment(name, namespace)
                containers = deployment.spec.template.spec.containers
            elif kind == 'StatefulSet':
                statefulset = self.apps_v1.read_namespaced_stateful_set(name, namespace)
                containers = statefulset.spec.template.spec.containers
            elif kind == 'DaemonSet':
                daemonset = self.apps_v1.read_namespaced_daemon_set(name, namespace)
                containers = daemonset.spec.template.spec.containers
            else:
                return {}

            current_resources = {}
            for container in containers:
                resources = container.resources
                current_resources[container.name] = {
                    'requests': resources.requests or {},
                    'limits': resources.limits or {}
                }

            return current_resources

        except Exception as e:
            logger.warning(f"Could not fetch current resources for {kind}/{name} in {namespace}: {e}")
            return {}

    def generate_console_report(self, vpas: List[Dict]) -> None:
        """Generate a console report using Rich tables."""
        if not vpas:
            self.console.print("[yellow]No VPA recommendations found.[/yellow]")
            return

        # Summary table
        summary_table = Table(title="VPA Recommendations Summary")
        summary_table.add_column("Namespace", style="cyan")
        summary_table.add_column("VPA Name", style="green")
        summary_table.add_column("Target", style="blue")
        summary_table.add_column("Update Mode", style="magenta")
        summary_table.add_column("Containers", justify="center")

        for vpa in vpas:
            summary_table.add_row(
                vpa['namespace'],
                vpa['name'],
                f"{vpa['target']['kind']}/{vpa['target']['name']}",
                vpa['updateMode'],
                str(len(vpa['recommendations']))
            )

        self.console.print(summary_table)

        # Detailed recommendations for each VPA
        for vpa in vpas:
            if not vpa['recommendations']:
                continue

            self.console.print(f"\n[bold blue]VPA: {vpa['namespace']}/{vpa['name']}[/bold blue]")
            self.console.print(f"Target: {vpa['target']['kind']}/{vpa['target']['name']}")

            for container_name, rec in vpa['recommendations'].items():
                detail_table = Table(title=f"Container: {container_name}")
                detail_table.add_column("Resource Type")
                detail_table.add_column("Current", style="yellow")
                detail_table.add_column("Lower Bound", style="red")
                detail_table.add_column("Target", style="green")
                detail_table.add_column("Upper Bound", style="blue")

                # CPU recommendations
                current_cpu = vpa['currentResources'].get(container_name, {}).get('requests', {}).get('cpu', 'N/A')
                detail_table.add_row(
                    "CPU",
                    self.format_resource_value(current_cpu, 'cpu'),
                    self.format_resource_value(rec['lowerBound'].get('cpu', 'N/A'), 'cpu'),
                    self.format_resource_value(rec['target'].get('cpu', 'N/A'), 'cpu'),
                    self.format_resource_value(rec['upperBound'].get('cpu', 'N/A'), 'cpu')
                )

                # Memory recommendations
                current_memory = vpa['currentResources'].get(container_name, {}).get('requests', {}).get('memory', 'N/A')
                detail_table.add_row(
                    "Memory",
                    self.format_resource_value(current_memory, 'memory'),
                    self.format_resource_value(rec['lowerBound'].get('memory', 'N/A'), 'memory'),
                    self.format_resource_value(rec['target'].get('memory', 'N/A'), 'memory'),
                    self.format_resource_value(rec['upperBound'].get('memory', 'N/A'), 'memory')
                )

                self.console.print(detail_table)

    def generate_json_report(self, vpas: List[Dict], output_path: str) -> None:
        """Generate a JSON report."""
        report = {
            'metadata': {
                'generatedAt': datetime.now().isoformat(),
                'totalVPAs': len(vpas),
                'generator': 'vpa-goldilocks-reporter'
            },
            'vpas': vpas
        }

        output_file = Path(output_path)
        with output_file.open('w') as f:
            json.dump(report, f, indent=2, default=str)

        self.console.print(f"[green]JSON report generated: {output_path}[/green]")

    def generate_yaml_report(self, vpas: List[Dict], output_path: str) -> None:
        """Generate a YAML report."""
        report = {
            'metadata': {
                'generatedAt': datetime.now().isoformat(),
                'totalVPAs': len(vpas),
                'generator': 'vpa-goldilocks-reporter'
            },
            'vpas': vpas
        }

        output_file = Path(output_path)
        with output_file.open('w') as f:
            yaml.dump(report, f, indent=2, default_flow_style=False)

        self.console.print(f"[green]YAML report generated: {output_path}[/green]")

    def generate_markdown_report(self, vpas: List[Dict], output_path: str) -> None:
        """Generate a Markdown report."""
        try:
            markdown_content = self._create_markdown_template(vpas)

            output_file = Path(output_path)
            with output_file.open('w') as f:
                f.write(markdown_content)

            self.console.print(f"[green]Markdown report generated: {output_path}[/green]")
        except Exception as e:
            logger.error(f"Error generating Markdown report: {e}")
            raise

    def _create_markdown_template(self, vpas: List[Dict]) -> str:
        """Create Markdown template for the report."""
        # Calculate summary stats
        vpas_with_recs = len([vpa for vpa in vpas if vpa.get('recommendations')])
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        markdown = f"""# 🎯 VPA Goldilocks Resource Recommendations Report

## 📊 Summary

- **Generated:** {timestamp}
- **Total VPAs:** {len(vpas)}
- **VPAs with Recommendations:** {vpas_with_recs}

---

"""

        if not vpas:
            markdown += "No VPA recommendations found.\n"
            return markdown

        # Add VPA details
        for vpa in vpas:
            vpa_name = f"{vpa.get('namespace', 'unknown')}/{vpa.get('name', 'unknown')}"
            target_name = f"{vpa.get('target', {}).get('kind', 'unknown')}/{vpa.get('target', {}).get('name', 'unknown')}"
            update_mode = str(vpa.get('updateMode', 'Off'))

            markdown += f"""## 🔧 VPA: {vpa_name}

- **Target:** {target_name}
- **Update Mode:** {update_mode}

"""

            if not vpa.get('recommendations'):
                markdown += "*No recommendations available*\n\n"
                continue

            # Add container recommendations
            for container_name, rec in vpa.get('recommendations', {}).items():
                current = vpa.get('currentResources', {}).get(container_name, {})

                markdown += f"""### 📦 Container: {container_name}

| Resource | Current Request | Lower Bound | Target | Upper Bound |
|----------|----------------|-------------|---------|-------------|
"""

                # CPU row
                current_cpu = current.get('requests', {}).get('cpu', 'N/A')
                lower_cpu = rec.get('lowerBound', {}).get('cpu', 'N/A')
                target_cpu = rec.get('target', {}).get('cpu', 'N/A')
                upper_cpu = rec.get('upperBound', {}).get('cpu', 'N/A')

                markdown += f"| **CPU** | {self.format_resource_value(current_cpu, 'cpu')} | {self.format_resource_value(lower_cpu, 'cpu')} | **{self.format_resource_value(target_cpu, 'cpu')}** | {self.format_resource_value(upper_cpu, 'cpu')} |\n"

                # Memory row
                current_memory = current.get('requests', {}).get('memory', 'N/A')
                lower_memory = rec.get('lowerBound', {}).get('memory', 'N/A')
                target_memory = rec.get('target', {}).get('memory', 'N/A')
                upper_memory = rec.get('upperBound', {}).get('memory', 'N/A')

                markdown += f"| **Memory** | {self.format_resource_value(current_memory, 'memory')} | {self.format_resource_value(lower_memory, 'memory')} | **{self.format_resource_value(target_memory, 'memory')}** | {self.format_resource_value(upper_memory, 'memory')} |\n\n"

        markdown += """---

*Generated by vpa-goldilocks-reporter*
"""

        return markdown

    def generate_kubectl_patches(self, vpas: List[Dict], output_path: str) -> None:
        """Generate kubectl patch commands for applying VPA recommendations."""
        patches = []

        for vpa in vpas:
            if not vpa['recommendations']:
                continue

            target = vpa['target']
            namespace = vpa['namespace']

            for container_name, rec in vpa['recommendations'].items():
                # Create patch for target recommendation
                patch = {
                    'op': 'replace',
                    'path': f"/spec/template/spec/containers/[?(@.name=='{container_name}')]/resources/requests",
                    'value': {}
                }

                if 'cpu' in rec['target']:
                    patch['value']['cpu'] = self.format_resource_value(rec['target']['cpu'], 'cpu')
                if 'memory' in rec['target']:
                    patch['value']['memory'] = self.format_resource_value(rec['target']['memory'], 'memory')

                kubectl_cmd = f"""# Apply VPA recommendation for {namespace}/{target['name']} container {container_name}
kubectl patch {target['kind'].lower()} {target['name']} -n {namespace} --type='json' -p='[{json.dumps(patch)}]'
"""
                patches.append(kubectl_cmd)

        output_file = Path(output_path)
        with output_file.open('w') as f:
            f.write('\n'.join(patches))

        self.console.print(f"[green]Kubectl patch commands generated: {output_path}[/green]")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate VPA Goldilocks resource recommendation reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --format console
  %(prog)s --format json --output vpa-report.json
  %(prog)s --format markdown --output vpa-report.md --namespace media
  %(prog)s --format yaml --output vpa-report.yaml --kubeconfig ~/.kube/config
  %(prog)s --format kubectl --output apply-recommendations.sh
  %(prog)s --format console --insecure  # For clusters with self-signed certificates
        """
    )

    parser.add_argument(
        '--format',
        choices=['console', 'json', 'yaml', 'markdown', 'kubectl'],
        default='console',
        help='Output format for the report (default: console)'
    )

    parser.add_argument(
        '--output',
        help='Output file path (required for non-console formats)'
    )

    parser.add_argument(
        '--namespace',
        help='Specific namespace to analyze (default: all namespaces)'
    )

    parser.add_argument(
        '--kubeconfig',
        help='Path to kubeconfig file (default: use in-cluster or default kubeconfig)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--insecure',
        action='store_true',
        help='Disable SSL certificate verification (useful for self-signed certs)'
    )

    parser.add_argument(
        '--show-ssl-warnings',
        action='store_true',
        help='Show SSL warnings (they are suppressed by default)'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle SSL warnings
    if not args.show_ssl_warnings:
        # SSL warnings are already disabled by default, but this makes it explicit
        warnings.filterwarnings('ignore', message='Unverified HTTPS request')

    if args.format != 'console' and not args.output:
        parser.error(f"--output is required when using --format {args.format}")

    try:
        reporter = VPARecommendationReporter(args.kubeconfig, args.insecure)
        vpas = reporter.get_vpa_recommendations(args.namespace)

        if args.format == 'console':
            reporter.generate_console_report(vpas)
        elif args.format == 'json':
            reporter.generate_json_report(vpas, args.output)
        elif args.format == 'yaml':
            reporter.generate_yaml_report(vpas, args.output)
        elif args.format == 'markdown':
            reporter.generate_markdown_report(vpas, args.output)
        elif args.format == 'kubectl':
            reporter.generate_kubectl_patches(vpas, args.output)

    except KeyboardInterrupt:
        print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
