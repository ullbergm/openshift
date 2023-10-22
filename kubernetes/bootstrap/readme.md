# Bootstrap

## OKE

download //OKE// openshift-install
```sh
./openshift-install coreos print-stream-json | grep location |grep x86_64 | grep iso
````

download iso (ex. https://builds.coreos.fedoraproject.org/prod/streams/stable/builds/37.20230401.3.0/x86_64/fedora-coreos-37.20230401.3.0-live.x86_64.iso) and save as boot.iso

download //OKD// openshift-install
```sh
mkdir okd
cat <<EOF
apiVersion: v1
baseDomain: your.base.domain
compute:
- name: worker
  replicas: 0
controlPlane:
  name: master
  replicas: 1
metadata:
  name: openshift
networking:
  clusterNetwork:
  - cidr: 10.128.0.0/14
    hostPrefix: 23
  machineNetwork:
  - cidr: 10.0.0.0/16
  networkType: OVNKubernetes
  serviceNetwork:
  - 172.30.0.0/16
platform:
  none: {}
bootstrapInPlace:
  installationDisk: /dev/sda
pullSecret: '{"auths":{"fake":{"auth":"aWQ6cGFzcwo="}}}'
sshKey: |
  ssh-rsa AAAAB...snip...YcvRRkMx your@email.address
EOF
./openshift-install --dir=ocp create single-node-ignition-config
podman run --privileged --pull always --rm -v /dev:/dev \
 -v /run/udev:/run/udev -v $PWD:/data -w /data quay.io/coreos/coreos-installer:release \
 iso ignition embed -fi okd/bootstrap-in-place-for-live-iso.ign boot.iso
```

write boot.iso to a thumbdrive using DD mode
boot the server with the thumbdrive
apply fix:
```sh
sudo groupadd hugetlbfs
sudo useradd openvswitch -n -G hugetlbfs -d / -v "Open vSwitch Daemons" -s /sbin/nologin
sudo systemctl start ovsdb-server.service
```
wait for it to reboot (twice?)

## Secrets

### Gitlab Deploy Key
```sh
ssh-keygen -t ecdsa -f github
kubectl -n flux-system create secret generic sops-age --from-file=age.agekey=age.agekey --dry-run=client -o yaml >age-key.yaml
sops --encrypt github-deploy-key.yaml > kubernetes/bootstrap/flux/github-deploy-key.sops.yaml
sops --decrypt kubernetes/bootstrap/flux/github-deploy-key.sops.yaml | oc apply -f -
```

add key to Gitlab repo

### SOPS AGE encryption key
```sh
age-keygen -o age.agekey
kubectl -n flux-system create secret generic sops-age --from-file=age.agekey=age.agekey --dry-run=client -o yaml >age-key.yaml
sops --encrypt age-key.yaml > kubernetes/bootstrap/flux/age-key.sops.yaml
sops --decrypt kubernetes/bootstrap/flux/age-key.sops.yaml | oc apply -f -
```

## Flux

### Install Flux

get your token after logging in to the cluster

```sh
oc login --token=sha256~pTLPMEs_...snip..._pthkBiyfHTS0E --server=https://api.openshift.your.domain:6443
oc apply --server-side --kustomize ./kubernetes/bootstrap/flux
```

```sh
oc apply --server-side --kustomize ./kubernetes/flux/config
```

```sh
FLUX_CONTROLLERS=(
"source-controller"
"kustomize-controller"
"helm-controller"
"notification-controller"
"image-reflector-controller"
"image-automation-controller"
)

for i in ${!FLUX_CONTROLLERS[@]}; do
  oc adm policy add-scc-to-user nonroot system:serviceaccount:${FLUX_NAMESPACE}:${FLUX_CONTROLLERS[$i]}
done
```
