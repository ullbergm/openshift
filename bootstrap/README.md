# Bootstrap cluster

1. Install OpenShift GitOps

2. Create cluster-config secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: cluster-config
  namespace: openshift-gitops
type: Opaque
stringData:
  config.yaml: |
    # becomes .Values.config
    cluster:
      top_level_domain: example.com
      name: cluster
      admin_email: YOUR_EMAIL
      timezone: YOUR_TIMEZONE
      storage:
        config:
          storageClassName: synology-iscsi
```

3. Create top level Argo Cluster definition

```yaml
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
        - name: config.cluster.name
          value: openshift
        - name: config.cluster.top_level_domain
          value: ullberg.local
        - name: spec.source.repoURL
          value: "https://github.com/ullbergm/openshift/"
        - name: spec.source.targetRevision
          value: v2
    path: cluster
    repoURL: "https://github.com/ullbergm/openshift/"
    targetRevision: v2
```
