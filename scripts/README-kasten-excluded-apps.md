# Kasten K10 Excluded Apps Management

This script automatically manages OpenShift-specific namespace exclusions for Kasten K10 backups by maintaining a separate file for system namespaces while preserving custom exclusions in the main values.yaml.

## Overview

OpenShift clusters have many system namespaces (all starting with `openshift-`) that should be excluded from Kasten K10 backups. This solution provides clean separation between:

- **OpenShift System Namespaces**: Automatically managed in `openshift-excluded-apps.yaml`
- **Custom Exclusions**: Manually managed in `values.yaml` under `kasten.excludedApps`
- **Static System Exclusions**: Hardcoded in the Helm template (cert-manager, kube-system, etc.)

The script automates the OpenShift namespace management by:

1. Querying the cluster for all namespaces matching `openshift*`
2. Writing them to a separate `openshift-excluded-apps.yaml` file
3. Creating timestamped backups before changes
4. Leaving custom exclusions untouched in values.yaml

## Usage

### Using Task (Recommended)

```bash
# Update OpenShift-specific namespace exclusions
task kasten:update-openshift-exclusions

# Preview changes without modifying files (dry-run)
task kasten:update-openshift-exclusions DRY_RUN=true

# Add a custom system namespace to static exclusions
task kasten:add-system-exclusion NAMESPACE=my-operator-system

# Remove a custom system namespace from static exclusions
task kasten:remove-system-exclusion NAMESPACE=my-operator-system
```

### Direct Script Execution

```bash
# Update the excluded apps list
./scripts/update-kasten-excluded-apps.sh

# Preview changes without modifying files (dry-run)
./scripts/update-kasten-excluded-apps.sh --dry-run
```

## What the script does

1. **Backup Creation**: Creates a timestamped backup of the current `openshift-excluded-apps.yaml` file
2. **Namespace Discovery**: Uses `kubectl get ns --no-headers=true | awk '/^openshift/{print $1}'` to find OpenShift namespaces
3. **Separate File Management**: Writes OpenShift namespaces to `openshift-excluded-apps.yaml`
4. **Custom Apps Preservation**: Leaves custom exclusions in `values.yaml` completely untouched
5. **Helm Integration**: The template automatically merges both sources during deployment
6. **Verification**: Provides a summary of changes made

## Dry-Run Mode

The script supports a dry-run mode that shows what changes would be made without actually modifying any files:

- **Preview Changes**: See exactly what the new excludedApps list would look like
- **No File Modifications**: Original values.yaml remains untouched
- **No Backup Creation**: Since no changes are made, no backup is needed
- **Full Validation**: All checks (kubectl connectivity, namespace discovery) still run

This is useful for:

- Verifying cluster connectivity before making changes
- Reviewing what namespaces would be added/removed
- Testing the script in CI/CD pipelines
- Auditing current vs. desired state

## When to run each task

### `kasten:update-openshift-exclusions`

- **After OpenShift upgrades**: New system namespaces may be introduced
- **Periodically**: As part of cluster maintenance (monthly/quarterly)
- **Before backup policy changes**: To ensure current state is captured
- **After installing new OpenShift operators**: Some operators create additional system namespaces

### `kasten:add-system-exclusion`

- **When deploying infrastructure operators**: Add operator namespaces to static exclusions
- **For cluster-level system components**: Add namespaces that should always be excluded
- **For non-OpenShift system namespaces**: Add namespaces like cert-manager, metallb-system, etc.

### `kasten:remove-system-exclusion`

- **When decommissioning infrastructure**: Remove no-longer-needed static exclusions
- **During cleanup operations**: Remove obsolete system namespace exclusions

## Example Output

```text
[INFO] Creating backup of values file: /workspaces/openshift/charts/infrastructure/k10-kasten-operator/values.yaml.backup.20250921_172114
[INFO] Fetching OpenShift-specific namespaces...
[INFO] Found 72 OpenShift namespaces to exclude
[INFO] Generating new excludedApps configuration...
[INFO] Preserving existing custom excluded apps...
[INFO] Updating values file...
[INFO] Successfully updated excludedApps list with 72 OpenShift namespaces
```

## Three Types of Exclusions

The solution manages three distinct types of namespace exclusions:

1. **Static System Exclusions**: Hardcoded in the Helm template

   - Common Kubernetes system namespaces (kube-system, cert-manager, etc.)
   - Infrastructure components that should always be excluded
   - Managed via `kasten:add-system-exclusion` and `kasten:remove-system-exclusion` tasks

2. **OpenShift System Exclusions**: Auto-generated from cluster

   - All namespaces starting with "openshift-"
   - Automatically discovered and managed
   - Updated via `kasten:update-openshift-exclusions` task

3. **Custom Application Exclusions**: User-defined in values.yaml
   - Application-specific namespaces to exclude
   - Manually managed in the values.yaml file
   - Examples: testing namespaces, temporary applications

## File Structure

The solution uses a clean separation of concerns:

### Custom Exclusions (`values.yaml`)

```yaml
kasten:
  # Custom applications to exclude from Kasten K10 backups
  # OpenShift system namespaces are automatically excluded via openshift-excluded-apps.yaml
  excludedApps:
    - startpunkt # Your custom excluded apps
    - another-app # Add more as needed
```

### OpenShift Exclusions (`openshift-excluded-apps.yaml`)

```yaml
# OpenShift System Namespaces to Exclude from Kasten K10 Backups
# This file is automatically generated by scripts/update-kasten-excluded-apps.sh
# Do not edit manually - it will be overwritten
#
# Generated on: 2025-09-21 17:27:19
# Cluster namespaces found: 72

# OpenShift system namespaces
excludedApps:
  - openshift
  - openshift-apiserver
  - openshift-authentication
  # ... all other OpenShift namespaces in alphabetical order
```

## Prerequisites

- `kubectl` must be installed and configured
- Active connection to the OpenShift cluster
- Write permissions to the values.yaml file

## Troubleshooting

- **"kubectl command not found"**: Install and configure kubectl
- **"Failed to connect to Kubernetes cluster"**: Check your kubeconfig and cluster connectivity
- **"No OpenShift namespaces found"**: Verify you're connected to an OpenShift cluster (not vanilla Kubernetes)

## Benefits of Separate File Approach

### Clear Separation of Concerns

- **OpenShift Namespaces**: System-managed, automatically updated
- **Custom Exclusions**: User-managed, preserved across updates
- **Static Exclusions**: Template-managed (cert-manager, kube-system, etc.)

### Easier Maintenance

- OpenShift upgrades won't affect your custom exclusions
- Clear visibility into what's automatic vs. manual
- Reduces risk of accidentally removing custom exclusions
- Git diffs show exactly what changed in each category

### Better Version Control

- Custom exclusions have meaningful commit history
- OpenShift namespace changes are clearly auto-generated
- Easier to review and approve changes

## Automation

Consider adding this to your cluster maintenance runbook or CI/CD pipeline to keep the excluded apps list current automatically.
