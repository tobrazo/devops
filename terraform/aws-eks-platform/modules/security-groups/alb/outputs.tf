output "alb_sg_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb_ingress.id
}
