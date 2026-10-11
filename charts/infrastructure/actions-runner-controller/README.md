# Actions Runner Controller

Self-hosted GitHub Actions runners on the cluster, using the upstream
[Actions Runner Controller](https://github.com/actions/actions-runner-controller)
runner scale sets. Runners are ephemeral: a pod is created per job and removed
when the job finishes, and nothing runs while no job is queued (apart from the
controller, the BuildKit daemon and one small listener pod per scale set).

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

## Building images

Runner pods have no Docker daemon. Image builds go to a shared rootless BuildKit
daemon in the same namespace, through the buildx `remote` driver:

```yaml
      - uses: docker/setup-buildx-action@v4
        with:
          driver: remote
          endpoint: tcp://buildkit.actions-runner-controller.svc:1234

      - uses: docker/build-push-action@v7
        with:
          push: true
          tags: ghcr.io/owner/image:tag
```

`docker/login-action`, `docker/metadata-action` and registry or `type=gha`
caching work unchanged. BuildKit runs under the `nested-container` SCC: inside a
pod user namespace, non-root, with only SETUID/SETGID. Its layer cache is an
`emptyDir`, lost when the pod restarts.

## Limitations

Runner pods run under the `nonroot-v2` SCC as UID 1001 with all capabilities
dropped. Consequently:

- Only `docker buildx build` works, as above. `docker run`, `load: true`,
  `container:` jobs, service containers and Docker-based actions do not.
- Builds are for the cluster's architecture only (no QEMU emulation).
- `sudo` does not work, so workflows cannot `apt-get install`. Use `setup-*`
  actions, which install into the runner's home directory.

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
