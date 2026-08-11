output "eip_ids" {
  description = "Allocated EIP IDs for NLB"
  value       = aws_eip.nlb[*].id
}

output "ingress_nginx_service" {
  description = "Ingress NGINX service info"
  value       = helm_release.this.status
}
