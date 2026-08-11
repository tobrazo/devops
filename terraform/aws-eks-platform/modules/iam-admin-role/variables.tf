variable "role_name" {
  type        = string
  description = "Name of the IAM admin role"
  default     = "eks-admin-role"
}

variable "trusted_account_arn" {
  type        = string
  description = "ARN of the user or role allowed to assume this admin role"
}
