
variable "name" { type = string }
variable "namespace" { type = string }
variable "chart_version" { type = string }
variable "values" {
  description = "List of rendered YAML strings for Helm values"
  type        = list(string)
  default     = []
}