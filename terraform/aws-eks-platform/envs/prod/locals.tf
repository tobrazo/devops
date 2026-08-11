########################################
# Locals (naming & tags)
########################################

locals {
  env     = "prod"
  project = "tobrazo"

  # Consistent, searchable tags across all resources
  tags = {
    Environment = local.env
    Project     = local.project
    ManagedBy   = "terraform"
  }

  # Allow public API from anywhere (you rely on IAM/RBAC)
  api_allow_cidrs = ["0.0.0.0/0"]

  # Cloudflare secrets from JSON vars
  cloudflare_external_dns_secret       = jsondecode(var.cloudflare_external_dns_json)
  cloudflare_cert_manager_secret       = jsondecode(var.cloudflare_cert_manager_json)
  cloudflare_cert_manager_front_secret = jsondecode(var.cloudflare_cert_manager_front_json)

  # Kubernetes namespaces
  external_dns_namespace = "kube-system"
  cert_manager_namespace = "cert-manager"
  argocd_namespace       = "argocd"

  # ArgoCD
  argocd_hostname = "argocd.example.com"

  # Application secrets (decoded from JSON)
  b2b_web_secret_map     = jsondecode(var.b2b_web_secrets_json)
  nestjs_back_secret_map = jsondecode(var.nestjs_app_secrets_back_json)
}