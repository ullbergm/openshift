# Actions Runner Controller

Self-hosted GitHub Actions runners on the cluster, using the upstream
[Actions Runner Controller](https://github.com/actions/actions-runner-controller)
runner scale sets. Runners are ephemeral: a pod is created per job and removed
when the job finishes, and nothing runs while no job is queued (apart from the
controller and one small listener pod per scale set).

## How it is put together

- The controller comes from the upstream `gha-runner-scale-set-controller` chart.
- This chart renders one `AutoscalingRunnerSet` per repository itself. The
  upstream `gha-runner-scale-set` chart is one Helm release per scale set, which
  does not fit a list of repositories in values.
- GitHub has no account-wide runners for a personal account, so each repository
  is registered separately. For an organization, set `scope: organization` and a
  single scale set serves every repository in it.

## Configuration

Set in the cluster values (`config.actions-runner-controller.*`):

| Key | Description |
|-----|-------------|
| `owner` | GitHub user or organization that owns the repositories |
| `repositories` | Repository names, comma-separated or a list |
| `scope` | `repository` (default) or `organization` |
| `runnerScaleSetName` | Value for `runs-on:` in workflows (default `openshift`) |
| `minRunners` / `maxRunners` | Per scale set (default `0` / `3`) |
| `auth.type` | `app` (default) or `token` |

## Credentials

Read from the `external-secrets` ClusterSecretStore.

GitHub App (`auth.type: app`): create an app with repository permissions
**Administration: read and write** and **Metadata: read** (for organization
scope: organization permission **Self-hosted runners: read and write**), install
it on the repositories, then store:

- `GITHUB_ACTIONS_RUNNER_APP_ID`
- `GITHUB_ACTIONS_RUNNER_APP_INSTALLATION_ID`
- `GITHUB_ACTIONS_RUNNER_APP_PRIVATE_KEY`

Personal access token (`auth.type: token`): a token with the `repo` scope (or a
fine-grained token with Administration read and write on the repositories),
stored as `GITHUB_ACTIONS_RUNNER_TOKEN`.

## Using the runners

```yaml
jobs:
  build:
    runs-on: openshift
```

## What the runners can do

Each runner pod has its own Docker daemon and passwordless `sudo`, so workflows
written for `ubuntu-latest` mostly run unchanged: `docker build`,
`docker/build-push-action`, `container:` jobs, `services:`, Docker-based actions
and `sudo apt-get install` all work.

The upstream runner image is minimal. The packages in `runner.packages`
(compiler toolchain, `gh`, ...) are installed with apt each time a runner pod
starts, which adds to job start-up time. Other tools GitHub-hosted runners ship
with need a `setup-*` action or an `apt-get install` step.

## Scheduling

Runner pods are pinned to dedicated worker nodes by `runner.affinity`. The
control plane nodes are schedulable and carry the worker role as well, so the
affinity excludes them explicitly. Jobs stay pending if no dedicated worker is
available. The controller and listener pods are not restricted.

## Security model

The Docker daemon sidecar in each runner pod runs **privileged**, which is
effectively root on the node for anything a workflow executes. This is a
deliberate exception to the cluster's "no privileged containers without a
hardware rationale" rule:

- A Docker daemon needs to manage cgroups, mounts and network namespaces.
  Running it inside a pod user namespace (`hostUsers: false`) was tried and does
  not work on this cluster: the daemon cannot write its cgroup tree.
- Only repositories listed in `repositories` get runners. Keep that list to
  private repositories where every contributor is trusted, and never add a
  public repository that runs workflows from forks.

The runner container itself runs as UID 1001 with `sudo`; the chart's SCC grants
no host namespaces, host paths or host ports.

## Limitations

- Builds are for the cluster's architecture only unless the workflow sets up
  QEMU.
- Nothing is cached between jobs: every runner pod starts with an empty Docker
  daemon. Use registry or `type=gha` build caches.

GitHub stops accepting runners that fall too far behind the current release, so
keep the Renovate updates for `ghcr.io/actions/actions-runner` merged.

## Troubleshooting

```bash
# Controller and listeners
oc logs -n actions-runner-controller -l app.kubernetes.io/name=gha-rs-controller
oc get pods -n actions-runner-controller

# Scale sets and their runners
oc get autoscalingrunnersets,ephemeralrunners -n actions-runner-controller
```
