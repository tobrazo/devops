variable "enable_metrics_server" {
  type        = string
  default     = "true"
  description = "metrics for Horizontal Pod Autoscaler"
}

variable "metrics_server_version" {
  type    = string
  default = "3.12.2"
}
