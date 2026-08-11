variable "name" {
  type        = string
  description = "Release name"
}

variable "namespace" {
  type        = string
  default     = "ingress-nginx"
  description = "Namespace to install"
}

variable "chart_version" {
  type        = string
  default     = "4.10.0"
  description = "Chart version of ingress-nginx"
}

variable "eip_count" {
  type        = number
  default     = 3
  description = "Number of Elastic IPs to allocate for NLB"
}
