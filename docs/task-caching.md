# Task Caching

This repository uses Taskfile's built-in caching capabilities to avoid re-running validation tasks when the source files haven't changed. This significantly speeds up development workflows, especially for CI/CD pipelines and frequent validation runs.

## How It Works

Tasks use checksums of source files to determine if they need to be re-run. If the source files haven't changed since the last successful run, the task is skipped.

### Cached Tasks

The following tasks are cached and will only run when their source files change:

#### Validation Tasks

- **`validate:adr`** - Cached based on `docs/decisions/*.md` and `scripts/validate-adr.sh`
- **`helm:validation`** - Cached based on all Helm chart files (`charts/**/Chart.yaml`, `charts/**/values.yaml`, `charts/**/templates/**/*.yaml`)
- **`helm:lint`** - Cached based on all Helm chart files
- **`helm:validate-icons`** - Cached based on `charts/**/values.yaml` and `scripts/validate-icons.sh`
- **`helm:validate-icons-offline`** - Cached based on `charts/**/values.yaml` and `scripts/validate-icons.sh`

#### Git Tasks

- **`git:pre-commit`** - Cached based on all files and `.pre-commit-config.yaml`

### Cache Storage

Cache files are stored in `.task-cache/` directory which is:

- Ignored by Git (added to `.gitignore`)
- Automatically created when tasks run
- Contains checksum files that track the state of source files

### Cache Management

#### Clearing Cache

To force all tasks to run regardless of file changes:

```bash
task clean
```

This removes the entire `.task-cache/` directory, forcing all cached tasks to run on their next execution.

#### Cache Behavior

- **First Run**: Tasks always execute and create cache files
- **Subsequent Runs**: Tasks check if source files have changed
  - If unchanged: Task is skipped with message "Task [name] is up to date"
  - If changed: Task executes and updates cache

#### Debugging Cache

Use verbose mode to see caching behavior:

```bash
task -v validate:adr
```

## Benefits

1. **Faster Development**: Skip validation when files haven't changed
2. **Efficient CI/CD**: Reduce pipeline execution time
3. **Better Developer Experience**: Immediate feedback on which tasks actually need to run
4. **Resource Savings**: Avoid redundant computation

## Best Practices

1. **Always use `task clean`** when troubleshooting task behavior
2. **Source file patterns** are inclusive - if you add new file types that should trigger validation, update the task's `sources` list
3. **Generated files** (like `.task-cache/helm-validation.txt`) should never be committed to Git
4. **Cache invalidation** happens automatically when source files change, no manual intervention needed

## Technical Details

The caching uses Taskfile's `method: checksum` which:

- Calculates checksums of all files matching the `sources` patterns
- Stores checksums in the `generates` file
- Compares current checksums with stored ones to determine if task should run
- Only runs the task if checksums don't match or the generates file doesn't exist
