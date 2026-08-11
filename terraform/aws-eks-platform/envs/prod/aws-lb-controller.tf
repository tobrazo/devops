module "aws_lb_controller" {
  source               = "../../modules/helm/aws-lb-controller"
  cluster_name         = module.eks.cluster_name
  region               = "eu-central-1"
  vpc_id               = module.vpc.vpc_id
  oidc_provider_arn    = module.eks.oidc_provider_arn
  oidc_provider_url    = module.eks.oidc_provider
  service_account_name = "aws-load-balancer-controller"

  depends_on = [module.eks]
}
