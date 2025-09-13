# External Secrets Operator - Infisical Integration

This chart sets up a ClusterSecretStore for the External Secrets Operator to integrate with Infisical for centralized secret management.

## Overview

The External Secrets Operator allows you to use external secret management systems (like Infisical) as the source of truth for secrets in your Kubernetes cluster. This chart configures a ClusterSecretStore that connects to Infisical using Universal Auth credentials.

## Prerequisites

1. **External Secrets Operator** must be installed in the cluster
2. **OperatorConfig** object must be created
3. **Infisical project** with Universal Auth configured
4. **Universal Auth credentials** (Client ID and Client Secret) from Infisical

## Bootstrap Process

### Step 1: Create the Authentication Secret

Before deploying this chart, you need to manually create the authentication secret containing your Infisical Universal Auth credentials:

```bash
kubectl create secret generic infiscal-auth-secret \
  --from-literal=clientId="YOUR_INFISICAL_CLIENT_ID" \
  --from-literal=clientSecret="YOUR_INFISICAL_CLIENT_SECRET" \
  --namespace external-secrets
```

Replace `YOUR_INFISICAL_CLIENT_ID` and `YOUR_INFISICAL_CLIENT_SECRET` with your actual Infisical Universal Auth credentials.

### Step 2: Configure Values

Update the `values.yaml` file with your Infisical project details:

```yaml
externalSecrets:
  secret: infiscal-auth-secret # Name of the secret created in Step 1
  infisical:
    projectSlug: your-project-slug # Your Infisical project slug
    environmentSlug: prod # Environment (prod, dev, staging, etc.)
```

### Step 3: Deploy the Chart

Once the secret is created and values are configured, deploy the chart through your GitOps process. The chart will create a ClusterSecretStore named `infisical` that can be used by ExternalSecret resources throughout the cluster.

## Usage

After the ClusterSecretStore is deployed, you can create ExternalSecret resources in any namespace to pull secrets from Infisical:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: radarr-secret
  namespace: my-app
spec:
  refreshInterval: 5m
  secretStoreRef:
    kind: ClusterSecretStore
    name: external-secrets # References the ClusterSecretStore created by this chart
  target:
    name: radarr-secret
    creationPolicy: Owner
  data:
    - secretKey: database-password
      remoteRef:
        key: DATABASE_PASSWORD # Key in Infisical
```

To create a secret to be used for environment variables:

```yaml
---
# yaml-language-server: $schema=https://kubernetes-schemas.pages.dev/external-secrets.io/externalsecret_v1beta1.json
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: radarr
spec:
  secretStoreRef:
    kind: ClusterSecretStore
    name: external-secrets
  target:
    name: radarr-secret
    template:
      engineVersion: v2
      mergePolicy: Replace
      data:
        RADARR__AUTH__APIKEY: "{{ .RADARR_API_KEY }}"

  dataFrom:
    - find:
        path: RADARR_API_KEY
```

## Configuration

### Values

| Parameter                                   | Description                                                         | Default                |
| ------------------------------------------- | ------------------------------------------------------------------- | ---------------------- |
| `externalSecrets.secret`                    | Name of the Kubernetes secret containing Infisical auth credentials | `infiscal-auth-secret` |
| `externalSecrets.infisical.projectSlug`     | Infisical project slug                                              | `openshift`            |
| `externalSecrets.infisical.environmentSlug` | Infisical environment slug                                          | `prod`                 |

### Infisical Configuration

The ClusterSecretStore is configured to:

- Pull secrets from the root path (`/`) recursively
- Use the Infisical cloud instance (`https://app.infisical.com`)
- Authenticate using Universal Auth credentials stored in Kubernetes secrets
