{{/*
Release-derived name, DNS-label safe. Same pattern as every chart in this repo.
*/}}
{{- define "vt.fullname" -}}
{{- default .Release.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "vt.exporterName" -}}
{{ include "vt.fullname" . }}-exporter
{{- end -}}

{{- define "vt.mockName" -}}
{{ include "vt.fullname" . }}-mock
{{- end -}}

{{- define "vt.triageName" -}}
{{ include "vt.fullname" . }}-triage
{{- end -}}

{{- define "vt.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{/*
The cabinet host the exporter talks to. With the mock enabled it is the
in-cluster mock Service, so a demo install needs no other override.
*/}}
{{- define "vt.pandoraHost" -}}
{{- if .Values.mock.enabled -}}
{{ include "vt.mockName" . }}:8080
{{- else -}}
{{ .Values.pandora.host }}
{{- end -}}
{{- end -}}

{{- define "vt.pandoraScheme" -}}
{{- if .Values.mock.enabled -}}http{{- else -}}{{ .Values.pandora.scheme }}{{- end -}}
{{- end -}}

{{- define "vt.pandoraSecretName" -}}
{{- default (printf "%s-pandora" (include "vt.fullname" .)) .Values.pandora.existingSecret -}}
{{- end -}}

{{- define "vt.triageSecretName" -}}
{{- default (printf "%s-triage" (include "vt.fullname" .)) .Values.triage.existingSecret -}}
{{- end -}}
