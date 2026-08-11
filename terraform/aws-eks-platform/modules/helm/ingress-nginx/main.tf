resource "aws_eip" "nlb" {
  count = var.eip_count

  tags = {
    Name = "${var.name}-eip-${count.index + 1}"
  }
}


locals {
  rendered_values = templatefile("${path.module}/values.tmpl.yaml", {
    eip_alloc_ips = aws_eip.nlb[*].id
  })
}



resource "helm_release" "this" {
  name             = var.name
  repository       = "https://kubernetes.github.io/ingress-nginx"
  chart            = "ingress-nginx"
  version          = var.chart_version
  namespace        = var.namespace
  create_namespace = true

  values = [local.rendered_values]

  depends_on = [aws_eip.nlb]

  timeout = 600
  atomic  = true

}


