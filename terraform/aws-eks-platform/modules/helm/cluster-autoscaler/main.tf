########################################
# Helm module: Cluster Autoscaler
########################################

variable "namespace" {
  type        = string
  description = "Namespace where Cluster Autoscaler will be installed"
  default     = "kube-system"
}

variable "chart_version" {
  type        = string
  description = "Cluster Autoscaler Helm chart version"
}

variable "region" {
  type        = string
  description = "AWS region"
}

variable "cluster_name" {
  type        = string
  description = "EKS cluster name"
}

variable "service_account_role_arn" {
  type        = string
  description = "IAM Role ARN for Cluster Autoscaler (via IRSA)"
}

resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  namespace  = var.namespace
  version    = var.chart_version

  create_namespace = false

  # AWS Region
  set {
    name  = "awsRegion"
    value = var.region
  }

  # EKS Cluster Name (for autodiscovery)
  set {
    name  = "autoDiscovery.clusterName"
    value = var.cluster_name
  }

  # ServiceAccount must exist (created by IRSA module)
  #set {
  #  name  = "serviceAccount.create"
  #  value = "false"
  #}
  set {
    name  = "rbac.serviceAccount.create"
    value = "false"
  }

  #set {
  #  name  = "serviceAccount.name"
  #  value = "cluster-autoscaler"
  #}

  set {
    name  = "rbac.serviceAccount.name"
    value = "cluster-autoscaler"
  }
  #set {
  #  name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
  #  value = var.service_account_role_arn
  #}
  #set {
  #  name  = "rbac.serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
  #  value = var.service_account_role_arn
  #}


  set {
    name  = "fullnameOverride"
    value = "cluster-autoscaler"
  }


  # Extra arguments for safe scaling
  set {
    name  = "extraArgs.skip-nodes-with-local-storage"
    value = "false"
  }

  set {
    name  = "extraArgs.scale-down-unneeded-time"
    value = "10m"
  }

  set {
    name  = "extraArgs.scale-down-delay-after-add"
    value = "2m"
  }

  set {
    name  = "extraArgs.balance-similar-node-groups"
    value = "true"
  }

  # Resources (tune if needed)
  set {
    name  = "resources.limits.cpu"
    value = "100m"
  }

  set {
    name  = "resources.limits.memory"
    value = "300Mi"
  }

  set {
    name  = "resources.requests.cpu"
    value = "100m"
  }

  set {
    name  = "resources.requests.memory"
    value = "300Mi"
  }
}
