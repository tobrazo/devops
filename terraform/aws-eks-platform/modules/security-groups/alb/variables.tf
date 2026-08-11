variable "vpc_id" {
  description = "VPC ID to associate with the ALB security group"
  type        = string
}

variable "name_prefix" {
  description = "Name prefix for ALB security group"
  type        = string
}
