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

{{/*
Whether any Claude feature is on, so the web-api needs the API key.
*/}}
{{- define "flow-analyzer.aiOn" -}}
{{- $cfg := index .Values "flow-analyzer" -}}
{{- if or $cfg.alertExplain.enabled $cfg.ai.identify $cfg.ai.digest $cfg.ai.logExplain $cfg.ai.ask -}}true{{- end -}}
{{- end }}
