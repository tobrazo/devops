variable "admin_role_arn" {
  description = "IAM Role or User ARN to grant cluster-admin via Access Entries."
  type        = string
}



variable "region" {
  type        = string
  description = "AWS region to deploy resources into"
}

variable "ghcr_creds_dockerconfigjson" {
  type        = string
  description = "JSON dockerconfig for GHCR pull secret"
  sensitive   = true
}

variable "b2b_web_secrets_json" {
  type        = string
  description = "JSON payload for b2b web secret"
  sensitive   = true
}

variable "nestjs_app_secrets_back_json" {
  type        = string
  description = "JSON payload for back service secret"
  sensitive   = true
}

variable "cloudflare_external_dns_json" {
  type        = string
  description = "JSON payload with Cloudflare API token for external-dns (e.g. {\"api-token\":\"...\"})"
  sensitive   = true
}

variable "cloudflare_cert_manager_json" {
  type        = string
  description = "JSON payload with Cloudflare API token for cert-manager DNS solver"
  sensitive   = true
}

variable "cloudflare_cert_manager_front_json" {
  type        = string
  description = "JSON payload with Cloudflare API token for cert-manager DNS solver dedicated to example.com / example.net"
  sensitive   = true
}

variable "cert_manager_email" {
  type        = string
  description = "Email used for ACME registrations"
  default     = "admin@example.com"
}
variable "argocd_slack_webhook_url" {
  type        = string
  sensitive   = true
  description = "Slack webhook for Argo CD notifications"
}

variable "argocd_repo_ssh_private_key" {
  description = "Temporary dummy key for destroy"
  type        = string
  default     = ""
}

#variable "enable_argocd_root_app" {
#  description = "Enable ArgoCD Root App and dependent manifests"
#  type        = bool
#  default     = true
#}

variable "enable_k8s_post" {
  type    = bool
  default = true
}