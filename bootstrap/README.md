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

## Step 2: Give ArgoCD Cluster Admin rights

Create ClusterRoleBinding for ArgoCD

```bash
oc apply -f - <<EOF
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: openshift-gitops-argocd-application-controller-cluster-admin
subjects:
  - kind: ServiceAccount
    name: openshift-gitops-argocd-application-controller
    namespace: openshift-gitops
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
EOF
```

## Step 3: Create the Cluster Application

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
          value: "v2"
        - name: config.cluster.storage.config.storageClassName
          value: "your-storage-class"
    path: cluster
    repoURL: "https://github.com/YOUR_USERNAME/openshift"
    targetRevision: v2
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF
```

## Step 4: Customize Configuration

Replace the following placeholder values in the Application manifest above:

- `YOUR_EMAIL@example.com`: Your admin email address
- `YOUR_CLUSTER_NAME`: A name for your cluster (e.g., "homelab", "openshift")
- `America/New_York`: Your timezone (see [TZ database names](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones))
- `example.local`: Your cluster's top-level domain
- `YOUR_USERNAME`: Your GitHub username
- `your-storage-class`: Your preferred storage class (or omit the parameter to use cluster default)

## Step 5: Deploy and Verify

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
