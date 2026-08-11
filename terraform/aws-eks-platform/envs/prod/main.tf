########################################
# envs/prod/main.tf
# Minimal, production-grade EKS on AWS
# using terraform-aws-modules (VPC + EKS v20+)
########################################

terraform {
  # Store state in S3 with DynamoDB locking (one backend per environment!)
  backend "s3" {
    bucket         = "tobrazo-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "tobrazo-terraform-lock"
    encrypt        = true
  }

  required_version = ">= 1.5.0"

}




# IAM admin role for EKS access via IRSA or assume-role
module "admin_role" {
  source              = "../../modules/iam-admin-role"
  role_name           = "eks-admin-role-tobrazo"
  trusted_account_arn = "arn:aws:iam::000000000000:user/tobrazo"
}



########################################
# EFS
########################################

module "efs" {
  source = "../../modules/storage/efs"

  name                   = "${local.project}-${local.env}-efs"
  vpc_id                 = module.vpc.vpc_id
  subnet_ids             = module.vpc.private_subnets
  node_security_group_id = module.eks.node_security_group_id
  tags                   = local.tags

  transition_to_ia = "AFTER_30_DAYS"

  #kms_key_id              = aws_kms_key.efs.arn

}

########################################
# Minimal policy for EFS CSI driver
# (Create/Delete AccessPoint, Describe*, TagResource)
########################################


resource "aws_iam_policy" "efs_csi_min" {
  name        = "${local.project}-${local.env}-efs-csi-min"
  description = "Minimal permissions for AWS EFS CSI controller"
  policy      = file("${path.module}/../../modules/irsa/policies/efs-csi-driver.json")
}

module "irsa_efs_csi_driver" {
  source = "../../modules/irsa"

  namespace            = "kube-system"
  service_account_name = "efs-csi-controller-sa"
  role_name            = "${local.project}-${local.env}-irsa-efs-csi-driver"

  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider

  managed_policy_arns    = [aws_iam_policy.efs_csi_min.arn]
  create_service_account = false
  tags                   = local.tags
}

########################################
# (Optional) KMS for EFS encryption
# - Attach policy to the actual key you create
# - Allow both IRSA role and the EFS service principal
########################################

data "aws_caller_identity" "current" {}

# KMS key for EFS encryption (enable only if you set kms_key_id on EFS)
resource "aws_kms_key" "efs" {
  description             = "KMS key for EFS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = local.tags
}

# KMS key policy that allows: IRSA role, EFS service, and account root
data "aws_iam_policy_document" "efs_kms_policy" {
  # Allow the IRSA role used by EFS CSI to use the key (for AP creation with encryption)
  statement {
    sid    = "AllowEFSCSIIRSAAccess"
    effect = "Allow"
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
      "kms:CreateGrant"
    ]
    principals {
      type        = "AWS"
      identifiers = [module.irsa_efs_csi_driver.role_arn]
    }
    resources = ["*"]
  }

  # Allow the EFS service itself to use the key (critical for encrypted EFS/AP)
  statement {
    sid    = "AllowEFSSvc"
    effect = "Allow"
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey*",
      "kms:DescribeKey",
      "kms:CreateGrant"
    ]
    principals {
      type        = "Service"
      identifiers = ["elasticfilesystem.amazonaws.com"]
    }
    resources = ["*"]
    # Optional: tighten with encryption context bound to your FS ARN
    # condition {
    #   test     = "StringEquals"
    #   variable = "kms:EncryptionContext:aws:elasticfilesystem:arn"
    #   values   = ["arn:aws:elasticfilesystem:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:file-system/${aws_efs_file_system.this.id}"]
    # }
  }

  # Full control for the account root (owner)
  statement {
    sid     = "AllowRootAccountAccess"
    effect  = "Allow"
    actions = ["kms:*"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    resources = ["*"]
  }
}

# IMPORTANT: attach policy to the KMS key you just created
resource "aws_kms_key_policy" "efs" {
  key_id = aws_kms_key.efs.key_id
  policy = data.aws_iam_policy_document.efs_kms_policy.json
}

########################################
# External Secrets IRSA
########################################

module "irsa_external_secrets" {
  source = "../../modules/irsa"

  namespace            = "external-secrets"
  service_account_name = "external-secrets-sa"
  role_name            = "${local.project}-${local.env}-irsa-external-secrets"

  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider

  managed_policy_arns    = ["arn:aws:iam::aws:policy/SecretsManagerReadWrite"]
  create_service_account = false
  tags                   = local.tags
}

###
##################################
# Grafana IRSA
##################################

resource "aws_iam_policy" "grafana_cloudwatch" {
  name        = "${local.project}-${local.env}-grafana-cloudwatch"
  description = "Permissions for Grafana to read CloudWatch metrics and logs"
  policy      = file("${path.module}/../../modules/irsa/policies/grafana-cloudwatch.json")
}

module "irsa_grafana" {
  source = "../../modules/irsa"

  namespace            = "monitoring"
  service_account_name = "grafana"
  role_name            = "${local.project}-${local.env}-irsa-grafana"

  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_provider_url = module.eks.oidc_provider

  managed_policy_arns    = [aws_iam_policy.grafana_cloudwatch.arn]
  service_account_labels = { app = "grafana" }
  create_service_account = true
  tags                   = local.tags
  depends_on             = [module.eks, kubernetes_namespace.monitoring]
}





