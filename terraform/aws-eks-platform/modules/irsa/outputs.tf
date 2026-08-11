output "role_arn" {
  value       = aws_iam_role.this.arn
  description = "ARN of the created IAM Role"
}

output "role_name" {
  value       = aws_iam_role.this.name
  description = "Name of the created IAM Role"
}