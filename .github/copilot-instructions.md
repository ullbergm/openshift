# OpenShift Cluster - Home Operations Repository

## Overview

This is a GitOps-managed Kubernetes home cluster running on OpenShift with Argo CD for automated deployments. The infrastructure follows Infrastructure as Code (IaC) principles with comprehensive monitoring, automation, and self-healing capabilities.

## Repository Structure

### Core Directories

- **`charts/`** - Kubernetes helm charts for all the applications organized by functional groups
- **`cluster/`** - Cluster definition and ApplicationSet templates for functional groups
- **`docs/`** - Documentation
- **`.taskfiles/`** - Task file definitions

## Key Patterns

### Template-Based Application Management

- Each functional group is managed by an ApplicationSet template in `cluster/templates/` (e.g., `media.yaml`, `ai.yaml`)
- ApplicationSets define which applications to deploy from the corresponding `/charts` subdirectory
- Applications automatically inherit cluster-wide configuration via Helm value passthrough

### Application Structure Standards

Every application chart follows these conventions:

- **Namespace isolation:** Each app runs in its own namespace (matches app name)
- **OpenShift Routes:** Use `.apps.{{ .Values.cluster.name }}.{{ .Values.cluster.top_level_domain }}` pattern
- **SecurityContextConstraints:** Required for OpenShift; grants ServiceAccount permissions
- **Kasten backup:** Add `kasten/backup: "true"` labels to StatefulSets for backup integration, NFS volumes are excluded from backups by adding `kasten/skip: "true"` to those volumes
- **Auto-reload:** Use `reloader.stakater.com/auto: "true"` for config changes

### Configuration Inheritance

Applications receive cluster config through values passthrough:

```yaml
# In ApplicationSet templates (e.g., cluster/templates/ai.yaml)
helm:
  valuesObject:
    spec:
{{ .Values.spec | toYaml | nindent 14 }}
{{ .Values.config | toYaml | nindent 12 }}
```

### Storage Patterns

**Storage Class Configuration:**

- Use conditional storage class assignment with fallback to cluster default:
  ```yaml
  {{- if .Values.cluster.storage.config.storageClassName }}
    storageClassName: {{ .Values.cluster.storage.config.storageClassName }}
  {{- end }}
  ```
- **Fallback Behavior:** When `storageClassName` is not specified in cluster configuration, templates fall back to the cluster's default storage class by omitting the `storageClassName` field entirely (Kubernetes-native approach)
- **Configuration Location:** `/cluster/values.yaml` → `cluster.storage.config.storageClassName`
- **Consistent Pattern:** All PersistentVolumeClaims use this conditional inclusion pattern

**Volume Sizing:**

- Config volumes typically 15Gi
- Data volumes larger (10Gi+)
- Media apps often use shared NFS storage

### Adding a New Application

1. Create namespace directory under `/charts/<group>/<app>/`
2. Create application helm chart
3. Add Application definition in `cluster/templates/[group].yaml` ApplicationSet

## OpenShift-Specific Requirements

### Mandatory Resources

- **ServiceAccount:** Required for pod execution
- **SecurityContextConstraints:** Grants necessary permissions to ServiceAccount
- **Route:** Provides external access with automatic TLS termination

### Value Template Patterns

**Standard Route Configuration:**

```yaml
host: {{ .Release.Name }}.apps.{{ .Values.cluster.name }}.{{ .Values.cluster.top_level_domain }}
```

**Timezone Inheritance:**

```yaml
# In values.yaml
pods:
  main:
    env:
      TZ: "{{ .Values.cluster.timezone }}"
```

- **Pattern:** All applications inherit timezone from `cluster.timezone`
- **Template-based:** Uses Helm templating to reference cluster configuration
- **Consistency:** All applications should use this inheritance pattern (avoid hardcoding)

**ServiceAccount Reference:**

```yaml
serviceAccountName: { { .Release.Name } }
```

## Configuration Management

### Cluster Configuration

- **Placeholder Values:** The `cluster/values.yaml` file contains placeholder values (e.g., `YOUR_REPO_URL`, `YOUR_EMAIL`) that are intended to be replaced during Argo CD bootstrapping
- **Bootstrap Process:** Real values are injected when the cluster is bootstrapped with Argo CD
- **Template Inheritance:** Applications inherit cluster configuration through Helm value passthrough

### Bootstrap Process Details

**Placeholder Values in cluster/values.yaml:**

- `repoURL: YOUR_REPO_URL`
- `admin_email: YOUR_EMAIL`
- `timezone: YOUR_TIMEZONE`
- `top_level_domain: example.com`
- `name: cluster`

**Bootstrap Flow:**

1. **Repository Setup:** The cluster repository is prepared with template placeholder values
2. **Bootstrap Script:** Argo CD bootstrap process injects actual configuration values
3. **Runtime Configuration:** Applications receive real values through Helm value passthrough
4. **GitOps Management:** Argo CD manages the cluster using the injected real values

**Why Placeholders:**

- **Security:** Prevents committing sensitive real values to version control
- **Portability:** Same repository template can be used for multiple cluster deployments
- **Bootstrap Flexibility:** Real values are environment-specific and injected at deployment time
- **Template Integrity:** Ensures the repository structure and patterns are validated before real deployment

## Critical Files

- `cluster/values.yaml` - Global configuration
- `cluster/templates/<group>.yaml` - ApplicationSet templates for each functional group
- `charts/*/templates/` - Kubernetes manifests for each application

## Important Notes

- This cluster represents a production-ready home lab environment with enterprise-grade tooling and practices scaled for personal use.
- Never commit unencrypted secrets.
- Follow the documented directory and naming conventions to ensure consistency.
- Validate Helm charts and manifests locally before pushing changes.
- Applications are managed through ApplicationSet templates in `cluster/templates/`.
- Backup critical cluster state and application data using the integrated Kasten solution.
- Review and update SecurityContextConstraints and Routes when upgrading OpenShift versions.
- Document any manual interventions or exceptions in the `docs/` directory.
