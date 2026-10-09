{{/*
Name of the Secret holding CLICKHOUSE_PASSWORD and SNMP_COMMUNITY: the
ExternalSecret target, the Secret rendered by secret.yaml, or one supplied
through secrets.existingSecret.
*/}}
{{- define "flow-analyzer.secretName" -}}
{{- if and (not .Values.externalSecret.enabled) .Values.secrets.existingSecret -}}
{{ .Values.secrets.existingSecret }}
{{- else -}}
{{ .Release.Name }}
{{- end -}}
{{- end -}}
