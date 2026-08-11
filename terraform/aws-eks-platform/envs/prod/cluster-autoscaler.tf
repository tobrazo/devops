module "irsa_cluster_autoscaler" {
  source = "../../modules/irsa"

  namespace            = "kube-system"
  service_account_name = "cluster-autoscaler"
  role_name            = "${local.project}-${local.env}-irsa-cluster-autoscaler"

  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider

  policy_json = file("${path.module}/../../modules/irsa/policies/cluster-autoscaler.json")
  tags        = local.tags

  service_account_annotations = {
    "meta.helm.sh/release-name"      = "cluster-autoscaler"
    "meta.helm.sh/release-namespace" = "kube-system"
  }

  service_account_labels = {
    "app.kubernetes.io/managed-by" = "Helm"
  }

}


module "cluster_autoscaler" {
  source = "../../modules/helm/cluster-autoscaler"

  namespace                = "kube-system"
  chart_version            = "9.44.0"
  region                   = var.region
  cluster_name             = module.eks.cluster_name
  service_account_role_arn = module.irsa_cluster_autoscaler.role_arn

  depends_on = [module.irsa_cluster_autoscaler]
}