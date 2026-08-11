########################################
# EKS (community module v20+)
# - Uses Access Entries (no aws-auth configmap)
# - Private subnets for nodes
# - Public API endpoint (restricted CIDRs); consider private-only later
########################################

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "${local.project}-${local.env}-eks"
  cluster_version = "1.34"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # API endpoint exposure:
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  # When public access is enabled, allow only these source CIDRs (tighten ASAP)
  cluster_endpoint_public_access_cidrs = local.api_allow_cidrs

  # Control plane logs (helpful for audit/troubleshooting; costs apply)
  create_cloudwatch_log_group            = true
  cloudwatch_log_group_retention_in_days = 30
  cluster_enabled_log_types              = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # Modern access control (replaces legacy aws-auth)
  access_entries = {
    cluster_creator = {
      principal_arn = "arn:aws:iam::000000000000:user/tobrazo"
      policy_associations = {
        admin = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }

    admin_role = {
      principal_arn = module.admin_role.admin_role_arn
      policy_associations = {
        admin = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }
  }

  # Core EKS addons - let the module manage their lifecycle
  cluster_addons = {
    coredns            = {}
    kube-proxy         = {}
    vpc-cni            = {}
    aws-ebs-csi-driver = {}
    aws-efs-csi-driver = {
      service_account_role_arn = module.irsa_efs_csi_driver.role_arn
    }
  }

  # Managed node groups
  eks_managed_node_groups = {

    # NEW: single_az node group (only eu-central-1a)
    single_az = {
      enable_auto_scaling = true

      min_size     = 6
      max_size     = 7
      desired_size = 6

      instance_types = ["m6g.xlarge"]
      capacity_type  = "ON_DEMAND"
      ami_type       = "AL2023_ARM_64_STANDARD"

      # Critical: only one subnet → only eu-central-1a
      subnet_ids = [module.vpc.private_subnets[0]] # 10.0.1.0/24 = eu-central-1a

      tags = {
        "k8s.io/cluster-autoscaler/enabled"                           = "true"
        "k8s.io/cluster-autoscaler/${local.project}-${local.env}-eks" = "owned"
      }

      force_update_version = true

      update_config = {
        max_unavailable_percentage = 33
      }

      additional_security_group_ids = [module.eks_nodes_sg.eks_nodes_sg_id]

      iam_role_additional_policies = {
        ebs = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
      }
    }
  }

  # Propagate consistent tags
  tags = local.tags
}

# Update kubeconfig file to use the new EKS cluster
resource "time_sleep" "wait_for_eks" {
  depends_on      = [module.eks]
  create_duration = "90s"
}

resource "null_resource" "update_kubeconfig" {
  depends_on = [time_sleep.wait_for_eks]
  provisioner "local-exec" {
    command = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.region}"
  }
}