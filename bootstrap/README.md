# OpenShift Cluster Bootstrap Instructions

This document provides step-by-step instructions for bootstrapping an OpenShift cluster with Argo CD using this GitOps repository.

## Prerequisites

- OpenShift cluster (OKD 4.12+ or OpenShift 4.12+)
- `oc` CLI tool configured and authenticated to the cluster
- `kubectl` CLI tool (optional, but recommended)
- Cluster admin privileges

## Bootstrap Process Overview

The bootstrap process involves:

1. Installing Argo CD on the cluster
2. Creating the initial cluster Application that references this repository
3. Argo CD automatically deploying all applications based on the ApplicationSet templates

## Step 1: Install Argo CD

Install the Argo CD operator in the `openshift-gitops` namespace:

```bash
# Create the GitOps operator subscription
oc apply -f - <<EOF
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openshift-gitops-operator
  namespace: openshift-operators
spec:
  channel: latest
  installPlanApproval: Automatic
  name: openshift-gitops-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
```

Wait for the operator to be installed and the `openshift-gitops` namespace to be created:

```bash
oc get pods -n openshift-gitops
```

## Step 2: Create the Cluster Application

Create the main cluster Application that will manage all other applications:

```bash
oc apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: cluster
  namespace: openshift-gitops
spec:
  destination:
    namespace: openshift-gitops
    server: "https://kubernetes.default.svc"
  project: default
  source:
    helm:
      parameters:
        - name: config.cluster.admin_email
          value: "YOUR_EMAIL@example.com"
        - name: config.cluster.name
          value: "YOUR_CLUSTER_NAME"
        - name: config.cluster.timezone
          value: "America/New_York"
        - name: config.cluster.top_level_domain
          value: "example.local"
        - name: spec.source.repoURL
          value: "https://github.com/YOUR_USERNAME/openshift"
        - name: spec.source.targetRevision
          value: "main"
        - name: config.cluster.storage.config.storageClassName
          value: "your-storage-class"
    path: cluster
    repoURL: "https://github.com/YOUR_USERNAME/openshift"
    targetRevision: main
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF
```

## Step 3: Customize Configuration

Replace the following placeholder values in the Application manifest above:

- `YOUR_EMAIL@example.com`: Your admin email address
- `YOUR_CLUSTER_NAME`: A name for your cluster (e.g., "homelab", "openshift")
- `America/New_York`: Your timezone (see [TZ database names](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones))
- `example.local`: Your cluster's top-level domain
- `YOUR_USERNAME`: Your GitHub username
- `your-storage-class`: Your preferred storage class (or omit the parameter to use cluster default)

## Step 4: Deploy and Verify

After applying the cluster Application, Argo CD will:

1. Deploy the cluster configuration
2. Create ApplicationSets for each functional group:
   - AI/ML applications
   - Infrastructure applications
   - Media applications
   - Productivity applications
   - Security applications

Monitor the deployment progress:

```bash
# Check Argo CD Applications
oc get applications -n openshift-gitops

# Check ApplicationSets
oc get applicationsets -n openshift-gitops

# Monitor application sync status
oc get applications -n openshift-gitops -w
```

## Step 5: Access Argo CD UI

Get the Argo CD admin password:

```bash
oc get secret openshift-gitops-cluster -n openshift-gitops -o jsonpath='{.data.admin\.password}' | base64 -d
```

Access the Argo CD UI via the OpenShift route:

```bash
oc get route openshift-gitops-server -n openshift-gitops
```

Login with username `admin` and the password from above.

## Troubleshooting

### Application Sync Issues

If applications fail to sync:

1. Check the Application status: `oc describe application APP_NAME -n openshift-gitops`
2. Verify the source repository is accessible
3. Check for RBAC issues in the application namespace
4. Review the Argo CD application controller logs

### Storage Class Issues

If applications fail due to storage class issues:

1. List available storage classes: `oc get storageclass`
2. Update the cluster configuration to use an available storage class
3. Or omit the storage class parameter to use the cluster default

### Network Policy Issues

If applications can't communicate:

1. Check if network policies are blocking traffic
2. Verify the applications are deployed in the correct namespaces
3. Check OpenShift Routes are created and accessible

## Post-Bootstrap Configuration

After successful bootstrap, you may want to:

1. Configure external secrets if using the External Secrets Operator
2. Set up backup schedules for applications with persistent data
3. Configure monitoring and alerting through the infrastructure applications
4. Customize application configurations by modifying their respective Helm charts

## Security Considerations

- Ensure your Git repository is private if it contains sensitive configuration
- Use external secret management for sensitive data (External Secrets Operator is included)
- Regularly update the Argo CD operator and applications
- Monitor the cluster for security vulnerabilities using the included security tools
