# Bootstrap

## OKE

download openshift-install

```sh
sudo groupadd hugetlbfs
sudo useradd openvswitch -n -G hugetlbfs -d / -v "Open vSwitch Daemons" -s /sbin/nologin
sudo systemctl start ovsdb-server.service
```

## Secrets

```sh
age-keygen -o age.key
```

## Flux

### Install Flux

```sh
kubectl apply --server-side --kustomize ./kubernetes/bootstrap/flux
```

