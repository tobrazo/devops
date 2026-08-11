########################################
# Ingress NGINX
########################################
module "ingress_nginx" {
  source = "../../modules/helm/ingress-nginx"

  name          = "ingress-nginx"
  namespace     = "ingress-nginx"
  chart_version = "4.10.0"

  depends_on = [module.eks]
}


########################################
# ArgoCD Core Installation via Helm
########################################
module "argocd" {
  source = "../../modules/helm/argocd"

  name          = "argocd"
  namespace     = local.argocd_namespace
  chart_version = "9.0.3"

  values = [
    templatefile("${path.module}/../../modules/helm/argocd/values.yaml", {
      hostname          = local.argocd_hostname
      slack_webhook_url = var.argocd_slack_webhook_url
      enable_tls        = true
      tls_secret_name   = "argocd-tls"
      cluster_issuer    = "letsencrypt-dns"
    })
  ]

  depends_on = [
    module.eks,
    module.ingress_nginx,
    helm_release.cert_manager,
    helm_release.external_dns
  ]
}


########################################
# Kubernetes Metrics Server Helm Chart
########################################
module "kubernetes_metrics_server" {
  source                 = "../../modules/helm/kubernetes-metrics-server"
  metrics_server_version = "3.12.2"
  depends_on             = [module.eks]
}


########################################
# ExternalDNS (backend)
########################################
resource "helm_release" "external_dns" {
  name             = "tf-external-dns"
  repository       = "https://kubernetes-sigs.github.io/external-dns/"
  chart            = "external-dns"
  namespace        = local.external_dns_namespace
  create_namespace = false

  set {
    name  = "provider.name"
    value = "cloudflare"
  }

  set {
    name  = "env[0].name"
    value = "CF_API_TOKEN"
  }

  set {
    name  = "env[0].valueFrom.secretKeyRef.name"
    value = kubernetes_secret.cloudflare_external_dns.metadata[0].name
  }

  set {
    name  = "env[0].valueFrom.secretKeyRef.key"
    value = "api-token"
  }

  set {
    name  = "sources[0]"
    value = "service"
  }

  set {
    name  = "sources[1]"
    value = "ingress"
  }

  ### tmp policy change
  #  set {
  #    name  = "policy"
  #    value = "sync"
  #  }
  set {
    name  = "policy"
    value = "upsert-only"
  }

  set {
    name  = "registry"
    value = "txt"
  }

  set {
    name  = "txtPrefix"
    value = "_external-dns."
  }

  set {
    name  = "extraArgs[0]"
    value = "--cloudflare-proxied"
  }


  depends_on = [
    module.eks,
    module.ingress_nginx,
    kubernetes_secret.cloudflare_external_dns
  ]
}


########################################
# ExternalDNS (frontend)
########################################
resource "helm_release" "external_dns_front" {
  name             = "tf-external-dns-front"
  repository       = "https://kubernetes-sigs.github.io/external-dns/"
  chart            = "external-dns"
  namespace        = local.external_dns_namespace
  create_namespace = false

  set {
    name  = "provider.name"
    value = "cloudflare"
  }

  set {
    name  = "env[0].name"
    value = "CF_API_TOKEN"
  }

  set {
    name  = "env[0].valueFrom.secretKeyRef.name"
    value = kubernetes_secret.cloudflare_external_dns_front.metadata[0].name
  }

  set {
    name  = "env[0].valueFrom.secretKeyRef.key"
    value = "api-token"
  }

  set {
    name  = "sources[0]"
    value = "ingress"
  }

  ### tmp policy change
  #  set {
  #    name  = "policy"
  #    value = "sync"
  #  }
  set {
    name  = "policy"
    value = "upsert-only"
  }

  set {
    name  = "registry"
    value = "txt"
  }

  set {
    name  = "txtPrefix"
    value = "_external-dns-front."
  }

  set {
    name  = "txtOwnerId"
    value = "tobrazo-prod"
  }

  set {
    name  = "domainFilters[0]"
    value = "example.com"
  }

  set {
    name  = "domainFilters[1]"
    value = "example.net"
  }

  set {
    name  = "extraArgs[0]"
    value = "--cloudflare-proxied"
  }

  depends_on = [
    module.eks,
    module.ingress_nginx,
    kubernetes_secret.cloudflare_external_dns_front
  ]
}


########################################
# cert-manager
########################################
resource "helm_release" "cert_manager" {
  name             = "cert-manager"
  repository       = "https://charts.jetstack.io"
  chart            = "cert-manager"
  version          = "v1.15.3"
  namespace        = local.cert_manager_namespace
  create_namespace = false

  set {
    name  = "installCRDs"
    value = true
  }

  depends_on = [module.eks]
}



