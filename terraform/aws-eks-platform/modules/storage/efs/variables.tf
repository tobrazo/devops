variable "name" {
  description = "Name / creation token for EFS"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where EFS lives"
  type        = string
}

variable "subnet_ids" {
  description = "Subnets for Mount Targets (use private subnets)"
  type        = list(string)
}

variable "node_security_group_id" {
  description = "EKS node security group id; NFS will be allowed only from it"
  type        = string
}

variable "kms_key_id" {
  description = "KMS key for EFS encryption (optional)"
  type        = string
  default     = null
}

variable "transition_to_ia" {
  description = "Lifecycle transition to Infrequent Access (e.g. AFTER_30_DAYS); null to disable"
  type        = string
  default     = null
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
