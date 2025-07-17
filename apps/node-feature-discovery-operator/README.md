# node-feature-discovery-operator (Kustomize)

This directory contains the Kustomize manifests for deploying the node-feature-discovery-operator.

## Usage

To deploy using Kustomize:

```sh
kubectl apply -k ./apps/node-feature-discovery-operator/overlay/default
```

Edit the manifests in `overlay/` as needed for your environment.
