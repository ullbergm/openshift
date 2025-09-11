---
applyTo: "**"
---

# Adding a New Functional Group to the OpenShift Repository

When the user asks to "add a role", "create a role", "add a new role", or mentions creating functional groupings for applications, automatically follow these steps:

## Steps to Add a New Functional Group

1. **Create ApplicationSet Template**

   - Create a new ApplicationSet template file in `cluster/templates/` (e.g., `monitoring.yaml`)
   - File name should match the functional domain (e.g., `ai.yaml`, `media.yaml`, `monitoring.yaml`)

2. **Create ApplicationSet Template Content**

   - Use the following template structure:

   ```yaml
   apiVersion: argoproj.io/v1alpha1
   kind: ApplicationSet
   metadata:
     name: {{ .Release.Name }}-[GROUP_NAME]
   spec:
     ignoreApplicationDifferences:
       - jsonPointers:
           - /spec/syncPolicy
     goTemplate: true
     generators:
       - list:
           elements:
           - name: [APP_NAME_1]
           - name: [APP_NAME_2]
     template:
       metadata:
         name: '{{ "{{" }} .name {{ "}}" }}'
         namespace: "openshift-gitops"
       spec:
         ignoreDifferences:
         - kind: Application
           group: argoproj.io
           jsonPointers:
           - /spec/syncPolicy
         project: default
         destination:
           server: {{ .Values.spec.destination.server }}
           namespace: "openshift-gitops"
         syncPolicy:
           automated:
             prune: true
             selfHeal: true
         source:
           repoURL: {{ .Values.spec.source.repoURL }}
           path: charts/{{ "{{" }} default "[GROUP_NAME]" .group {{ "}}" }}/{{ "{{" }} .name {{ "}}" }}
           targetRevision: {{ .Values.spec.source.targetRevision }}
           helm:
             valuesObject:
               spec:
   {{ .Values.spec | toYaml | nindent 14 }}
   {{ .Values.config | toYaml | nindent 12 }}
   ```

3. **Create Charts Directory**

   - Create a corresponding directory in `/charts/` (e.g., `/charts/monitoring/`)
   - This will contain individual Helm charts for each application in this functional group

4. **Update README.md**

   - Add information about the new functional group in the repository structure section
   - Include a brief description of what applications this group manages

## Functional Group Naming Conventions

- Use lowercase names for template files
- Use descriptive functional names (e.g., `ai.yaml`, `media.yaml`, `monitoring.yaml`)
- Avoid abbreviations when possible
- Template file names should match the charts subdirectory names

## Example Functional Group Categories

- `ai` - AI/ML applications (LLMs, training tools, inference servers)
- `media` - Media management (Plex, Sonarr, Radarr, etc.)
- `monitoring` - Observability tools (Prometheus, Grafana, etc.)
- `development` - Dev tools (IDEs, CI/CD, code quality)
- `security` - Security tools (scanners, secrets management)
- `networking` - Network utilities and tools
- `storage` - Storage management and backup tools
- `utilities` - General utility applications
