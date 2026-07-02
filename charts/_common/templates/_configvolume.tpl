{{- define "common.configvolume" -}}
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ .Release.Name }}-config
  labels:
    app.kubernetes.io/name: {{ .Release.Name }}
    app.kubernetes.io/instance: {{ .Release.Name }}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: {{ .Values.application.configSize | default "15Gi" }}
{{- if and .Values.cluster.storage .Values.cluster.storage.config .Values.cluster.storage.config.storageClassName }}
  storageClassName: {{ .Values.cluster.storage.config.storageClassName }}
{{- end }}
{{- end }}
