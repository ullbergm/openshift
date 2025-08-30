---
applyTo: "**"
---

# Adding a New Role to the OpenShift Repository

When the user asks to "add a role", "create a role", "add a new role", or mentions creating functional groupings for applications, automatically follow these steps:

## Steps to Add a New Role

1. **Create Role Directory Structure**

   - Create a new directory for the role under `roles/`
   - Directory name should match the functional domain (e.g., `ai`, `media`, `development`, `monitoring`)

2. **Create Chart.yaml**

   - Inside the new role directory, create a `Chart.yaml` file with the following template:

   ```yaml
   apiVersion: v2
   description: A Helm chart for the [ROLE_NAME] role
   name: [ROLE_NAME]
   version: 1.0.0
   kubeVersion: ">=1.22.0-0"

   maintainers:
     - name: Magnus Ullberg
       email: magnus@ullberg.us
   ```

3. **Create Templates Directory**

   - Create a `templates/` directory within the role directory
   - This will contain YAML files for each application in this role

4. **Update README.md**

   - Add information about the new role in the repository structure section
   - Include a brief description of what applications this role manages

5. **Update Cluster Values (Optional but Recommended)**
   - Add the new role to the roles list in `/cluster/values.yaml`
   - This enables the role in the cluster deployment

## Role Naming Conventions

- Use lowercase names
- Use descriptive functional names (e.g., `ai`, `media`, `monitoring`, `development`)
- Avoid abbreviations when possible

## Example Role Categories

- `ai` - AI/ML applications (LLMs, training tools, inference servers)
- `media` - Media management (Plex, Sonarr, Radarr, etc.)
- `monitoring` - Observability tools (Prometheus, Grafana, etc.)
- `development` - Dev tools (IDEs, CI/CD, code quality)
- `security` - Security tools (scanners, secrets management)
- `networking` - Network utilities and tools
- `storage` - Storage management and backup tools
