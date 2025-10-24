# Set Bond MAC Address

A Helm chart for OpenShift that configures network interface bonding with automatic MAC address management. This chart creates a MachineConfig that sets up a bond interface using active-backup mode and ensures the bond uses the MAC address of the primary interface.

## Overview

This chart configures:

- A bond interface (default: `bond0`) in active-backup mode
- Two slave interfaces (primary and secondary) attached to the bond
- A systemd service that automatically copies the primary interface's MAC address to the bond
- NetworkManager configuration files for all interfaces

## Why This Chart?

When creating a bond interface in OpenShift/RHCOS, you may want the bond to use the MAC address of one of its physical interfaces. This is useful for:

- Maintaining consistent DHCP leases
- Preserving network policies tied to specific MAC addresses
- Ensuring seamless failover without network identity changes

## How It Works

1. **NetworkManager Configuration**: Creates connection profiles for:

   - Bond interface template with a placeholder MAC address
   - Primary interface (configured as bond slave)
   - Secondary interface (configured as bond slave)

2. **Systemd Service**: Runs before NetworkManager to:

   - Copy the bond template to create the actual bond configuration
   - Read the current MAC address from the primary interface
   - Update the bond configuration with the actual MAC address
   - Set proper file permissions

3. **MachineConfig**: Deploys all configuration files to the specified node role (master/worker)

## Configuration

### Values

| Parameter                         | Description                                                              | Default  |
| --------------------------------- | ------------------------------------------------------------------------ | -------- |
| `setBondMac.role`                 | OpenShift node role to apply the configuration to (`master` or `worker`) | `master` |
| `setBondMac.interfaces.bond`      | Name of the bond interface                                               | `bond0`  |
| `setBondMac.interfaces.primary`   | Name of the primary network interface (active in bond)                   | `eno1`   |
| `setBondMac.interfaces.secondary` | Name of the secondary network interface (backup in bond)                 | `enp3s0` |

### Example values.yaml

```yaml
setBondMac:
  role: master

  interfaces:
    bond: bond0
    primary: eno1
    secondary: enp3s0
```

## Installation

### Using Helm

```bash
# Install with default values
helm install set-bond-mac . --namespace openshift-machine-config-operator

# Install with custom interface names
helm install set-bond-mac . \
  --set setBondMac.interfaces.bond=bond1 \
  --set setBondMac.interfaces.primary=eth0 \
  --set setBondMac.interfaces.secondary=eth1 \
  --namespace openshift-machine-config-operator

# Apply to worker nodes instead of masters
helm install set-bond-mac . \
  --set setBondMac.role=worker \
  --namespace openshift-machine-config-operator
```

### Using Argo CD

This chart is designed to work with Argo CD. Add it to your ApplicationSet:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: set-bond-mac
  namespace: openshift-gitops
spec:
  project: default
  source:
    repoURL: <your-repo>
    path: charts/infrastructure/set-bond-mac
    targetRevision: HEAD
    helm:
      valuesObject:
        setBondMac:
          role: master
          interfaces:
            bond: bond0
            primary: eno1
            secondary: enp3s0
  destination:
    server: https://kubernetes.default.svc
    namespace: openshift-machine-config-operator
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## Bond Configuration Details

### Bond Mode

- **Mode**: `active-backup`
- **Primary**: Configured primary interface
- **MII Monitor**: 100ms

### Interface Behavior

- **Primary Interface**: Active interface, provides MAC address to bond
- **Secondary Interface**: Backup interface, used if primary fails
- **Autoconnect**: All interfaces auto-connect on boot
- **Priority**: Bond slaves have autoconnect-priority of 20

## Files Created

The MachineConfig creates the following files on target nodes:

| File                                                              | Purpose                               | Mode       |
| ----------------------------------------------------------------- | ------------------------------------- | ---------- |
| `/etc/NetworkManager/system-connections/<bond>.template`          | Bond configuration template           | 384 (0600) |
| `/etc/NetworkManager/system-connections/<primary>.nmconnection`   | Primary interface configuration       | 384 (0600) |
| `/etc/NetworkManager/system-connections/<secondary>.nmconnection` | Secondary interface configuration     | 384 (0600) |
| `/etc/systemd/system/fix-mac.service`                             | Systemd service for MAC address setup | 420 (0644) |
| `/usr/local/sbin/fix-mac.sh`                                      | Script to set bond MAC address        | 493 (0755) |

## Verification

After deployment, verify the configuration on target nodes:

```bash
# Check MachineConfig was created
oc get machineconfig | grep set-bond-mac

# Check node is updating (if applicable)
oc get nodes

# On the node (after reboot/update completes):
# Check bond interface
ip link show bond0

# Verify MAC addresses match
ip link show eno1 | grep link/ether
ip link show bond0 | grep link/ether

# Check bond status
cat /proc/net/bonding/bond0

# View NetworkManager connections
nmcli connection show
```

## Troubleshooting

### MachineConfig not applying

- Verify the node role matches the `setBondMac.role` value
- Check MachineConfigPool status: `oc get mcp`
- View MachineConfig operator logs

### Bond not created after node reboot

- Check systemd service status: `systemctl status fix-mac.service`
- View service logs: `journalctl -u fix-mac.service`
- Verify files were created in `/etc/NetworkManager/system-connections/`

### Wrong MAC address on bond

- Verify the primary interface name matches `setBondMac.interfaces.primary`
- Check the fix-mac.sh script: `cat /usr/local/sbin/fix-mac.sh`
- Check if the primary interface exists: `ip link show <primary>`

## Requirements

- OpenShift 4.x with Machine Config Operator
- Kubernetes version >= 1.31.0
- Node must have the specified network interfaces

## Notes

- **Node Reboot Required**: Applying a MachineConfig will trigger a node reboot
- **Role-Based**: Only nodes with the specified role will receive the configuration
- **Interface Names**: Ensure interface names match your hardware before deployment
- **Backup Configuration**: Consider backing up existing network configuration before applying

## License

This chart is part of the OpenShift home operations infrastructure.

## Maintainers

- Magnus Ullberg <magnus@ullberg.us>
