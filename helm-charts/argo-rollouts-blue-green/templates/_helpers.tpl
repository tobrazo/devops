{{- define "app.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}


{{/*
Return main host
*/}}
{{- define "app.mainHost" -}}
{{ .Values.domains.main }}
{{- end }}

{{/*
Return preview host
*/}}
{{- define "app.previewHost" -}}
{{ .Values.domains.preview }}
{{- end }}

{{/*
Return server base URL
*/}}
{{- define "app.serverUrl" -}}
https://{{ .Values.domains.main }}
{{- end }}

{{/*
Return public API URL
*/}}
{{- define "app.publicApiUrl" -}}
https://{{ .Values.domains.publicApi }}/api
{{- end }}

{{/*
Return frontend base URL
*/}}
{{- define "app.frontendUrl" -}}
https://{{ .Values.domains.frontend }}
{{- end }}
