########################################
# Universal IRSA Module
# Creates: IAM Role + trust policy + optional IAM policy + Kubernetes ServiceAccount
########################################

# ---- Trust policy for OIDC + ServiceAccount ----
data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [var.oidc_provider_arn] # OIDC provider from EKS
    }

    # Restrict the role to this exact ServiceAccount
    condition {
      test     = "StringEquals"
      variable = "${replace(var.oidc_provider_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account_name}"]
    }

    # Ensure the audience is STS
    condition {
      test     = "StringEquals"
      variable = "${replace(var.oidc_provider_url, "https://", "")}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

# ---- IAM Role ----
resource "aws_iam_role" "this" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.trust.json
  tags               = var.tags
}

# ---- Optional policy (created only when JSON is provided) ----
resource "aws_iam_policy" "this" {
  count       = var.policy_json == null ? 0 : 1
  name        = "${var.role_name}-policy"
  description = "IRSA policy for ${var.service_account_name}"
  policy      = var.policy_json
}

# ---- Attach inline policy to IAM role ----
resource "aws_iam_role_policy_attachment" "this" {
  count      = var.policy_json == null ? 0 : 1
  role       = aws_iam_role.this.name
  policy_arn = aws_iam_policy.this[0].arn
}

# ---- Attach managed policies, if requested ----
##resource "aws_iam_role_policy_attachment" "managed" {
##  for_each = toset(var.managed_policy_arns)

##  role       = aws_iam_role.this.name
##  policy_arn = each.value
##}

# ---- Attach managed policies, if requested ----
# 🧠 Terraform cannot handle dynamic sets from unknown values at plan time.
# We convert the list to a map with static keys to make planning deterministic.
resource "aws_iam_role_policy_attachment" "managed" {
  for_each = { for idx, arn in var.managed_policy_arns : idx => arn }

  role       = aws_iam_role.this.name
  policy_arn = each.value
}

###
# ---- Kubernetes ServiceAccount ----
# ⚠️ Requires the kubernetes provider pointing at your EKS cluster

resource "kubernetes_service_account" "this" {
  count = var.create_service_account ? 1 : 0

  metadata {
    name      = var.service_account_name
    namespace = var.namespace

    labels = var.service_account_labels

    annotations = merge(
      {
        "eks.amazonaws.com/role-arn" = aws_iam_role.this.arn
      },
      var.service_account_annotations
    )
  }
}

