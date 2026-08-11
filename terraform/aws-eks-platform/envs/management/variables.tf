########################################
# variables.tf
########################################

variable "region" {
  type        = string
  description = "AWS region — Frankfurt"
  default     = "eu-central-1"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type for Windows + PostgreSQL"
  default     = "t3.large" # 2 vCPU / 8 GB RAM
}

variable "windows_admin_password" {
  type        = string
  description = "Password for the Windows Administrator account (min 12 chars, must meet Windows complexity)"
  sensitive   = true
}

variable "rdp_allowed_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to connect via RDP (port 3389). Restrict to your office/VPN IPs."
  default     = ["0.0.0.0/0"]
}

variable "postgres_allowed_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to connect to PostgreSQL (port 5432). Defaults to VPC only."
  default     = []
}

variable "postgres_password" {
  type        = string
  description = "Password for the PostgreSQL superuser (postgres)"
  sensitive   = true
}

variable "root_volume_size_gb" {
  type        = number
  description = "Root EBS volume size in GB"
  default     = 100
}

variable "pgdata_volume_size_gb" {
  type        = number
  description = "Separate EBS volume size for PostgreSQL data dir (D:\\pgdata)"
  default     = 20
}
