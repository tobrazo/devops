#resource "kubernetes_namespace" "monitoring" {
#  metadata {
#    name = "monitoring"
#  }
#}

resource "helm_release" "kube_prometheus_stack" {
  name       = "kube-prometheus-stack"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  namespace  = "monitoring"
  version    = "61.3.0" # 

  values = [
    file("${path.module}/values/kube-prometheus.yaml")
  ]

  #depends_on = [
  #  kubernetes_namespace.monitoring
  #]
}
