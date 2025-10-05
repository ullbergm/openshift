# EMQX Operator

## Overview

The EMQX Operator provides Kubernetes-native deployment and management of [EMQX](https://www.emqx.io/), an open-source MQTT broker. This chart deploys the EMQX Operator to your OpenShift cluster using the upstream Helm chart from EMQX.

## What is EMQX?

EMQX is a highly scalable, distributed MQTT messaging broker that supports millions of concurrent connections. It's designed for IoT, Industrial IoT (IIoT), and real-time messaging applications.

## What Does This Operator Do?

The EMQX Operator simplifies the deployment and management of EMQX clusters on Kubernetes/OpenShift by:

- **Automated Deployment**: Deploy EMQX clusters using custom resources
- **Cluster Management**: Automate operations like upgrades, scaling, and configuration updates
- **Persistent Storage**: Manage data persistence automatically
- **High Availability**: Support for multi-replica EMQX clusters
- **Monitoring Integration**: Built-in metrics and monitoring capabilities

## Prerequisites

- OpenShift 4.x cluster
- Helm 3.x
- Cluster admin access

## Installation

### Deploy the Operator

The operator will be automatically deployed by Argo CD when added to the cluster ApplicationSet:

```bash
# The operator is deployed via the base ApplicationSet in cluster/templates/base.yaml
# It will create the emqx-operator-system namespace and install the operator
```

### Verify Installation

```bash
# Check if the operator is running
oc get pods -n emqx-operator-system

# Check the operator logs
oc logs -n emqx-operator-system -l control-plane=controller-manager
```

## Usage

### Deploy an EMQX Cluster

Once the operator is installed, you can deploy EMQX clusters using custom resources:

```yaml
apiVersion: apps.emqx.io/v2beta1
kind: EMQX
metadata:
  name: emqx
  namespace: emqx
spec:
  image: emqx/emqx:5.8.0
  coreTemplate:
    spec:
      replicas: 3
  listenersServiceTemplate:
    spec:
      type: LoadBalancer
```

Apply the configuration:

```bash
oc apply -f emqx-cluster.yaml
```

### Access the EMQX Dashboard

After deployment, you can access the EMQX dashboard:

```bash
# Get the service details
oc get svc -n emqx

# Port forward to access locally
oc port-forward -n emqx svc/emqx-dashboard 18083:18083

# Open http://localhost:18083 in your browser
# Default credentials: admin / public
```

## Configuration

### Operator Configuration

The operator behavior can be configured in `values.yaml`:

| Parameter                      | Description                                  | Default         |
| ------------------------------ | -------------------------------------------- | --------------- |
| `emqxOperator.singleNamespace` | Watch only the operator namespace            | `false`         |
| `emqxOperator.development`     | Enable development mode with verbose logging | `false`         |
| `emqxOperator.replicaCount`    | Number of operator replicas                  | `1`             |
| `emqxOperator.resources`       | Resource requests/limits for operator        | See values.yaml |

### EMQX Cluster Configuration

For detailed EMQX cluster configuration options, refer to:

- [EMQX Operator Documentation](https://docs.emqx.com/en/emqx-operator/latest/)
- [EMQX CRD Reference](https://github.com/emqx/emqx-operator/blob/main/docs/en_US/reference/v2beta1-reference.md)

## Examples

### Basic EMQX Cluster

```yaml
apiVersion: apps.emqx.io/v2beta1
kind: EMQX
metadata:
  name: emqx-basic
  namespace: emqx
spec:
  image: emqx/emqx:5.8.0
  coreTemplate:
    spec:
      replicas: 3
```

### EMQX with Persistent Storage

```yaml
apiVersion: apps.emqx.io/v2beta1
kind: EMQX
metadata:
  name: emqx-persistent
  namespace: emqx
spec:
  image: emqx/emqx:5.8.0
  coreTemplate:
    spec:
      replicas: 3
      volumeClaimTemplates:
        - metadata:
            name: emqx-data
          spec:
            accessModes:
              - ReadWriteOnce
            resources:
              requests:
                storage: 10Gi
```

### EMQX Enterprise

```yaml
apiVersion: apps.emqx.io/v2beta1
kind: EMQX
metadata:
  name: emqx-enterprise
  namespace: emqx
spec:
  image: emqx/emqx-enterprise:5.8.0
  coreTemplate:
    spec:
      replicas: 3
```

## Monitoring

The EMQX Operator and EMQX clusters expose Prometheus metrics:

```yaml
# ServiceMonitor for EMQX metrics
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: emqx
  namespace: emqx
spec:
  selector:
    matchLabels:
      apps.emqx.io/instance: emqx
  endpoints:
    - port: metrics
      interval: 30s
```

## Troubleshooting

### Operator Not Starting

```bash
# Check operator logs
oc logs -n emqx-operator-system -l control-plane=controller-manager

# Check operator events
oc get events -n emqx-operator-system
```

### EMQX Cluster Not Ready

```bash
# Check EMQX custom resource status
oc describe emqx -n emqx <emqx-name>

# Check EMQX pod logs
oc logs -n emqx -l apps.emqx.io/instance=<emqx-name>

# Check EMQX pod events
oc get events -n emqx
```

### Common Issues

1. **CRD Version Conflicts**: Ensure you're using compatible versions of EMQX and the operator
2. **Resource Constraints**: Check if the cluster has enough resources for EMQX pods
3. **Storage Issues**: Verify PVC provisioning if using persistent storage

## References

- [EMQX Official Website](https://www.emqx.io/)
- [EMQX Operator GitHub](https://github.com/emqx/emqx-operator)
- [EMQX Operator Documentation](https://docs.emqx.com/en/emqx-operator/latest/)
- [EMQX Documentation](https://docs.emqx.com/)
- [MQTT Protocol](https://mqtt.org/)

## Support

- [EMQX Community Forum](https://askemq.com/)
- [EMQX GitHub Issues](https://github.com/emqx/emqx-operator/issues)
- [EMQX Slack](https://slack-invite.emqx.io/)

## License

The EMQX Operator is licensed under the Apache License 2.0.
