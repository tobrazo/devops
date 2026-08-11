resource "kubernetes_namespace" "logs" {
  metadata { name = "logs" }
}

resource "helm_release" "loki" {
  name       = "loki"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki"
  namespace  = "logs"  #kubernetes_namespace.logs.metadata[0].name
  version    = "6.6.2" # 

  values = [
    file("${path.module}/values/loki.yaml")
  ]

  #depends_on = [
  #  kubernetes_namespace.logs
  #]
}
