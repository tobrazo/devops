
########################################
# Cloudflare Cluster Issuer
########################################
resource "kubernetes_manifest" "letsencrypt_cluster_issuer" {
  count = var.enable_k8s_post ? 1 : 0

  #provider = kubernetes

  manifest = {
    apiVersion = "cert-manager.io/v1"
    kind       = "ClusterIssuer"
    metadata = {
      name = "letsencrypt-dns"
    }
    spec = {
      acme = {
        server = "https://acme-v02.api.letsencrypt.org/directory"
        email  = var.cert_manager_email
        privateKeySecretRef = {
          name = "letsencrypt-dns-account-key"
        }
        solvers = [
          {
            selector = {
              dnsZones = ["example.com"]
            }
            dns01 = {
              cloudflare = {
                apiTokenSecretRef = {
                  name = kubernetes_secret.cloudflare_cert_manager.metadata[0].name
                  key  = "api-token"
                }
              }
            }
          },
          {
            selector = {
              dnsZones = ["example.com", "example.net"]
            }
            dns01 = {
              cloudflare = {
                apiTokenSecretRef = {
                  name = kubernetes_secret.cloudflare_cert_manager_secondary.metadata[0].name
                  key  = "api-token"
                }
              }
            }
          }
        ]
      }
    }
  }

  depends_on = [
    module.eks,
    helm_release.cert_manager,
    kubernetes_secret.cloudflare_cert_manager,
    kubernetes_secret.cloudflare_cert_manager_secondary
  ]
}

########################################
# ArgoCD Root Application (GitOps)
########################################
resource "kubernetes_manifest" "argocd_root_app" {
  count = var.enable_k8s_post ? 1 : 0
  #provider = kubernetes

  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      name      = "root"
      namespace = local.argocd_namespace
      labels = {
        "app.kubernetes.io/part-of" = "argocd"
      }
    }
    spec = {
      project = "default"
      source = {
        repoURL        = "git@github.com:tobrazo/automation.git"
        targetRevision = "main"
        path           = "gitops/envs/prod"
      }
      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = "argocd"
      }
      syncPolicy = {
        automated = {
          prune    = true
          selfHeal = true
        }
        syncOptions = [
          "CreateNamespace=true",
          "ApplyOutOfSyncOnly=true"
        ]
      }
    }
  }

  depends_on = [
    module.argocd,
    kubernetes_secret.argocd_repo_automation,
    module.eks
  ]
}