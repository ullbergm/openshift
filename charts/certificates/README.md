## TODO

[ ] Patch the ingress controller to use the new certs
        ---
        apiVersion: operator.openshift.io/v1
        kind: IngressController
        metadata:
        annotations:
            kustomize.toolkit.fluxcd.io/prune: disabled
            kustomize.toolkit.fluxcd.io/ssa: merge
        name: default
        namespace: openshift-ingress-operator
        spec:
        defaultCertificate:
            name: apps-wildcard-cert-tls

[ ] Patch the ingress controller to use the new certs
        ---
        apiVersion: operator.openshift.io/v1
        kind: ApiServer

        spec:
            servingCerts:
                namedCertificates:
                - names:
                - api.openshift.ullberg.family
                servingCertificate:
                    name: api-cert-tls