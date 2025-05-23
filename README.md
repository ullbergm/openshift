# OpenShift Cluster

# Steps
1. Build the Agent ISO and use it to build your cluster.
2. Manually install OpenShift GitOps
3. In Argo, add the repositories you need

    | type | name  | repository                                |
    |------|-------|-------------------------------------------|
    | helm | bjw-s | https://bjw-s.github.io/helm-charts       |
    | git  |       | https://github.com/ullbergm/openshift.git |

4. Add the cluster application to Argo

        apiVersion: argoproj.io/v1alpha1
        kind: Application
        metadata:
          name: cluster
          namespace: openshift-gitops
        spec:
          destination:
            server: 'https://kubernetes.default.svc'
          project: default
          source:
            helm:
                parameters:
                - name: certificates.aws.access_key_id
                  value: AKIAxxxxxxxxxET
                - name: certificates.aws.hosted_zone_id
                  value: Z1xxxxxxxxxJR
                - name: certificates.aws.region
                  value: us-east-1
                - name: certificates.aws.secret_access_key
                  value: huxxxxxxxxxxxxxxxxxxxx+s
                - name: cluster.admin_email
                  value: my@email.com
                - name: cluster.name
                  value: mycluster
                - name: cluster.timezone
                  value: America/New_York
                - name: cluster.top_level_domain
                  value: my.domain
                - name: certificates.issuer
                  value: production
                - name: democratic-csi.driver.config.httpConnection.host
                  value: nas.my.domain
                - name: democratic-csi.driver.config.httpConnection.password
                  value: supersecret!
                - name: democratic-csi.driver.config.httpConnection.username
                  value: synology-csi
                - name: democratic-csi.driver.config.iscsi.targetPortal
                  value: 10.0.0.10
                - name: spec.source.repoURL
                  value: 'https://github.com/ullbergm/openshift.git'
                - name: spec.source.targetRevision
                  value: main
                - name: spec.destination.server
                  value: 'https://kubernetes.default.svc'
            path: deploy/cluster
            repoURL: 'https://github.com/ullbergm/openshift.git'
            targetRevision: HEAD
        syncPolicy:
            automated:
                prune: true
                selfHeal: true

5. Add Argo cluster-admin

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

7. Customize ingress controller

      oc patch -n openshift-ingress-operator ingresscontroller/default --patch '{"spec":{"httpErrorCodePages":{"name":"custom-error-code-pages"}}}' --type=merge

6. Once the certificates are working, update the IngressController object with:

        spec:
            defaultCertificate:
                name: apps-wildcard-cert-tls

8. Update network config to have the allowedCIDRs

      spec:
        clusterNetwork:
          - cidr: 10.128.0.0/14
            hostPrefix: 23
        externalIP:
          policy:
            allowedCIDRs:
              - 192.168.0.0/24
        networkType: OVNKubernetes
        serviceNetwork:
          - 172.30.0.0/16