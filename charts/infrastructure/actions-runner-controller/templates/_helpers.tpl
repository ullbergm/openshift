{{/*
The runner scale sets to render, as a JSON list of {name, url}.
name is the Kubernetes resource name, url the GitHub registration scope.
*/}}
{{- define "actions-runner-controller.scaleSets" -}}
{{- $cfg := index .Values "actions-runner-controller" }}
{{- $sets := list }}
{{- if eq $cfg.scope "organization" }}
{{- $owner := required "actions-runner-controller.owner is required" $cfg.owner }}
{{- $sets = append $sets (dict "name" (include "actions-runner-controller.resourceName" $owner) "url" (printf "https://github.com/%s" $owner)) }}
{{- else }}
{{- $repos := $cfg.repositories | default list }}
{{- if kindIs "string" $repos }}
{{- $repos = splitList "," $repos }}
{{- end }}
{{- range $repos }}
{{- $repo := . | toString | trim }}
{{- if $repo }}
{{- $owner := required "actions-runner-controller.owner is required" $cfg.owner }}
{{- $sets = append $sets (dict "name" (include "actions-runner-controller.resourceName" $repo) "url" (printf "https://github.com/%s/%s" $owner $repo)) }}
{{- end }}
{{- end }}
{{- end }}
{{- $sets | toJson }}
{{- end }}

{{/*
A repository or organization name as a Kubernetes resource name.
The controller limits scale set resource names to 45 characters.
*/}}
{{- define "actions-runner-controller.resourceName" -}}
{{- $name := . | lower | replace "_" "-" | replace "." "-" | trimAll "-" }}
{{- if gt (len $name) 45 }}
{{- fail (printf "runner scale set name %q is longer than 45 characters" $name) }}
{{- end }}
{{- $name }}
{{- end }}

{{/*
Labels the controller expects on a scale set and its supporting resources.
Takes (dict "root" $ "name" <scale set name>).
*/}}
{{- define "actions-runner-controller.scaleSetLabels" -}}
{{- $ctrl := index .root.Subcharts "gha-runner-scale-set-controller" -}}
helm.sh/chart: gha-rs-{{ $ctrl.Chart.Version }}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/instance: {{ .name }}
app.kubernetes.io/version: {{ $ctrl.Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
app.kubernetes.io/part-of: gha-rs
actions.github.com/scale-set-name: {{ .name }}
actions.github.com/scale-set-namespace: {{ .root.Release.Namespace }}
{{- end }}
