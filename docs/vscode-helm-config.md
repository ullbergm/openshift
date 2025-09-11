# VS Code Configuration for Helm Templates

This workspace is configured to properly handle Helm template files without breaking the `{{ }}` syntax.

## Configuration Applied

### 1. File Associations

- Files in `charts/**/templates/*.yaml` are treated as `helm` files
- Files in `cluster/templates/*.yaml` are treated as `helm` files

### 2. Helm File Settings

- **Format on Save**: Disabled
- **Auto Indent**: Set to "keep" to preserve existing formatting
- **Default Formatter**: Disabled

### 3. YAML File Settings

- **Format on Save**: Disabled for all YAML files to prevent conflicts
- **Tab Size**: 2 spaces
- **Auto Indent**: Set to "keep"

### 4. Prettier Integration

- `.prettierignore` excludes Helm template directories
- Prettier respects the ignore file configuration

### 5. Recommended Extensions

- `ms-kubernetes-tools.vscode-kubernetes-tools` - Kubernetes support
- `tim-koehler.helm-intellisense` - Helm template IntelliSense

## Why This Configuration

VS Code's auto-formatting can break Helm template syntax by:

1. Adding spaces inside `{{ }}` expressions (making them `{ { }}`)
2. Reformatting YAML structure in ways incompatible with Helm
3. Breaking Go template logic and functions

This configuration preserves the integrity of Helm templates while still providing:

- Syntax highlighting
- Basic YAML validation (where appropriate)
- IntelliSense support for Kubernetes resources

## Manual Formatting

If you need to format Helm templates manually:

1. Use `helm template` to validate syntax
2. Use `yamllint` for YAML structure validation (configured to ignore templates)
3. Format manually following Kubernetes and Helm best practices
