# OpenShift Cluster

# Steps
1. Build the Agent ISO and use it to build your cluster.
2. Manually install OpenShift GitOps
3. In Argo, add the repository that holds your code.
4. Also in Argo, add a reference to any Helm repos you need.
5. Add the cluster application to Argo
6. Update the IngressController object with:
        spec:
        defaultCertificate:
            name: apps-wildcard-cert-tls
