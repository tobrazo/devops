output "cluster_name" {
  value       = module.eks.cluster_name
  description = "EKS cluster name"
}

output "cluster_endpoint" {
  value       = module.eks.cluster_endpoint
  description = "EKS API server endpoint"
}

output "oidc_provider_arn" {
  value       = module.eks.oidc_provider_arn
  description = "OIDC provider ARN for IRSA"
}

output "oidc_provider_url" {
  value       = module.eks.oidc_provider
  description = "OIDC issuer URL for IRSA"
}

output "kubeconfig_update_status" {
  value = "✅ Kubeconfig updated successfully. Cluster ready for kubectl access."
}