########################################
# VPC (community module)
# - Private subnets for worker nodes (recommended for prod)
# - Public subnets for ALBs/NLBs
# - Single NAT for cost; multi-NAT for HA if required
########################################

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${local.project}-${local.env}"
  cidr = "10.0.0.0/16"

  azs             = ["eu-central-1a", "eu-central-1b", "eu-central-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true

  # Tag subnets for Kubernetes load balancers (important!)
  # Public subnets for internet-facing LBs:
  public_subnet_tags = {
    "kubernetes.io/role/elb"                                  = "1"
    "kubernetes.io/cluster/${local.project}-${local.env}-eks" = "shared"
  }
  # Private subnets for internal LBs + nodes:
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"                         = "1"
    "kubernetes.io/cluster/${local.project}-${local.env}-eks" = "shared"
  }

  tags = local.tags
}

#########################################
# Security Groups
#########################################

module "eks_nodes_sg" {
  source      = "../../modules/security-groups"
  vpc_id      = module.vpc.vpc_id
  name_prefix = "${local.project}-${local.env}"
}

module "alb_sg" {
  source      = "../../modules/security-groups/alb"
  vpc_id      = module.vpc.vpc_id
  name_prefix = "${local.project}-${local.env}"
}