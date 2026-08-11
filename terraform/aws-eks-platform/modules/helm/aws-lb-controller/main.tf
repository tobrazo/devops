# Get EKS cluster and auth info
data "aws_eks_cluster" "this" {
  name = var.cluster_name

}

data "aws_eks_cluster_auth" "this" {
  name = var.cluster_name
}

# Trust policy: allow only this specific service account to assume the role
data "aws_iam_policy_document" "this" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(var.oidc_provider_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:${var.service_account_name}"]
    }
  }
}

# IAM Role for the AWS Load Balancer Controller
resource "aws_iam_role" "this" {
  name               = "${var.cluster_name}-alb-controller"
  assume_role_policy = data.aws_iam_policy_document.this.json
}

# Custom IAM policy for ALB Controller (loaded from file)
resource "aws_iam_policy" "custom_alb_policy" {
  name        = "${var.cluster_name}-alb-controller-policy"
  description = "Custom policy for AWS Load Balancer Controller"
  policy      = file("${path.module}/alb-controller-policy.json")
}

# Attach the custom IAM policy to the role
resource "aws_iam_role_policy_attachment" "this" {
  role       = aws_iam_role.this.name
  policy_arn = aws_iam_policy.custom_alb_policy.arn
}

# Kubernetes ServiceAccount with IAM role annotation (IRSA)
resource "kubernetes_service_account" "this" {
  metadata {
    name      = var.service_account_name
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.this.arn
    }
  }
}

# Install aws-load-balancer-controller via Helm
resource "helm_release" "this" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = "1.7.1"
  namespace  = "kube-system"

  create_namespace = false
  depends_on       = [kubernetes_service_account.this]

  set {
    name  = "region"
    value = var.region
  }

  set {
    name  = "vpcId"
    value = var.vpc_id
  }

  set {
    name  = "clusterName"
    value = var.cluster_name
  }

  set {
    name  = "serviceAccount.name"
    value = var.service_account_name
  }

  set {
    name  = "serviceAccount.create"
    value = "false"
  }
}
