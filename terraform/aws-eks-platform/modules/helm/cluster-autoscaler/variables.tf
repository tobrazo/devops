#variable "enable" {
#  description = "Toggle to enable/disable Cluster Autoscaler"
#  type        = bool
#  default     = true
#}

variable "timeout" {
  description = "Helm release timeout (seconds)"
  type        = number
  default     = 600
}


