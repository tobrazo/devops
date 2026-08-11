
resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
  }
  depends_on = [module.eks]
}

resource "kubernetes_namespace" "prod" {
  metadata {
    name = "prod"
  }
  depends_on = [module.eks]
}

resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
  }
  depends_on = [module.eks]
}

resource "kubernetes_namespace" "cert_manager" {
  metadata {
    name = "cert-manager"
  }
  depends_on = [module.eks]
}

########################################
# k8s Secrets for Prod Environment
########################################

resource "kubernetes_secret" "cloudflare_external_dns" {
  metadata {
    name      = "cloudflare-external-dns-token"
    namespace = local.external_dns_namespace
  }

  data = {
    "api-token" = local.cloudflare_external_dns_secret["api-token"]
  }

  type       = "Opaque"
  depends_on = [module.eks, kubernetes_namespace.prod]
}


#########################################
# Cloudflare External DNS Front Secret
#########################################
resource "kubernetes_secret" "cloudflare_external_dns_front" {
  metadata {
    name      = "cloudflare-external-dns-token-front"
    namespace = local.external_dns_namespace
  }

  data = {
    "api-token" = local.cloudflare_cert_manager_front_secret["api-token"]
  }

  type       = "Opaque"
  depends_on = [module.eks]
}


#######################################
# Cloudflare Cert-Manager Secret
#######################################
resource "kubernetes_secret" "cloudflare_cert_manager" {
  metadata {
    name      = "cloudflare-api-token-secret"
    namespace = local.cert_manager_namespace
  }

  data = {
    "api-token" = local.cloudflare_cert_manager_secret["api-token"]
  }

  type       = "Opaque"
  depends_on = [module.eks, kubernetes_namespace.cert_manager]
}

#######################################
# Cloudflare Cert-Manager Front Secret
#######################################

resource "kubernetes_secret" "cloudflare_cert_manager_front" {
  metadata {
    name      = "cloudflare-api-token-secret-front"
    namespace = local.cert_manager_namespace
  }

  data = {
    "api-token" = local.cloudflare_cert_manager_front_secret["api-token"]
  }

  type       = "Opaque"
  depends_on = [module.eks, kubernetes_namespace.cert_manager]
}


##########################################
# GHCR Credentials for Prod Workloads
##########################################
resource "kubernetes_secret" "ghcr_creds_prod" {
  metadata {
    name      = "ghcr-creds"
    namespace = "prod"
  }

  data = {
    ".dockerconfigjson" = var.ghcr_creds_dockerconfigjson
  }

  type       = "kubernetes.io/dockerconfigjson"
  depends_on = [module.eks, kubernetes_namespace.prod]
}


##########################################
# GHCR Credentials for ArgoCD
##########################################
resource "kubernetes_secret" "ghcr_creds_argocd" {
  metadata {
    name      = "ghcr-creds"
    namespace = "argocd"
  }

  data = {
    ".dockerconfigjson" = var.ghcr_creds_dockerconfigjson
  }

  type       = "kubernetes.io/dockerconfigjson"
  depends_on = [module.eks, kubernetes_namespace.argocd]
}


#########################################
# B2B Web Secrets
#########################################
resource "kubernetes_secret" "b2b_web_prod" {
  metadata {
    name      = "b2b-web-secrets"
    namespace = "prod"
  }

  data = local.b2b_web_secret_map

  type       = "Opaque"
  depends_on = [module.eks, kubernetes_namespace.prod]
}

#########################################
# NestJS App Secrets
#########################################
resource "kubernetes_secret" "nestjs_back_prod" {
  metadata {
    name      = "nestjs-app-secrets-back"
    namespace = "prod"
  }

  data = local.nestjs_back_secret_map

  type       = "Opaque"
  depends_on = [module.eks, kubernetes_namespace.prod]
}

########################################
# ArgoCD Git Repository Secret
########################################
resource "kubernetes_secret" "argocd_repo_automation" {
  metadata {
    name      = "repo-automation"
    namespace = local.argocd_namespace
    labels = {
      "argocd.argoproj.io/secret-type" = "repository"
    }
    annotations = {
      "managed-by" = "terraform"
    }
  }

  data = {
    name          = "ssh automation"
    url           = "git@github.com:tobrazo/automation.git"
    type          = "git"
    project       = "default"
    insecure      = "true"
    sshPrivateKey = var.argocd_repo_ssh_private_key
  }

  type       = "Opaque"
  depends_on = [module.argocd, module.ingress_nginx, module.eks]
}