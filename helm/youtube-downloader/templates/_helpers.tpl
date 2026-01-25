{{/*
_helpers.tpl - Reusable template snippets
These are like functions you can call from other templates
*/}}

{{/*
Create a default fully qualified app name.
We use release name + chart name, truncated to 63 chars (k8s limit)
Usage in templates: {{ include "youtube-downloader.fullname" . }}
*/}}
{{- define "youtube-downloader.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels applied to all resources
Usage: {{ include "youtube-downloader.labels" . | nindent 4 }}
*/}}
{{- define "youtube-downloader.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels (subset used for pod selection)
*/}}
{{- define "youtube-downloader.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
