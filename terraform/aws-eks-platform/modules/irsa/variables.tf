variable "oidc_provider_arn" {
  description = "ARN of the EKS OIDC provider"
  type        = string
}

variable "oidc_provider_url" {
  description = "URL of the EKS OIDC provider (without https://)"
  type        = string
}

variable "namespace" {
  description = "Kubernetes namespace for the ServiceAccount"
  type        = string
}

variable "service_account_name" {
  description = "Name of the Kubernetes ServiceAccount"
  type        = string
}

variable "role_name" {
  description = "IAM Role name"
  type        = string
}

variable "policy_json" {
  description = "IAM policy JSON (use file() or null if not needed)"
  type        = string
  default     = null
}

variable "managed_policy_arns" {
  description = "List of additional IAM policy ARNs to attach to the role"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags for IAM Role"
  type        = map(string)
  default     = {}
}

variable "create_service_account" {
  description = "Whether to create the Kubernetes ServiceAccount"
  type        = bool
  default     = true
}

variable "service_account_annotations" {
  description = "Additional annotations to apply to the ServiceAccount"
  type        = map(string)
  default     = {}
}

variable "service_account_labels" {
  description = "Additional labels to apply to the ServiceAccount"
  type        = map(string)
  default     = {}
}
