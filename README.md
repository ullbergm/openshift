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
                - name: backup.nfs.path
                  value: /volume1/backup
                - name: backup.nfs.server
                  value: nas.my.domain
                - name: network.node0.storageIp.ip
                  value: 10.0.0.20
                - name: network.node1.storageIp.ip
                  value: 10.0.0.21
                - name: network.node2.storageIp.ip
                  value: 10.0.0.22
            path: deploy/cluster
            repoURL: 'https://github.com/ullbergm/openshift.git'
            targetRevision: HEAD
        syncPolicy:
            automated:
                prune: true
                selfHeal: true

5. Once the certificates are working, update the IngressController object with:

        spec:
            defaultCertificate:
                name: apps-wildcard-cert-tls

6. Update the synology-iscsi VolumeSnapshotClass to have this annotation:

       k10.kasten.io/is-snapshot-class: true