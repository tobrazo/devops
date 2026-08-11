########################################
# locals.tf
########################################

locals {
  env     = "management"
  project = "tobrazo"

  tags = {
    Environment = local.env
    Project     = local.project
    ManagedBy   = "terraform"
  }

  name_prefix = "${local.project}-${local.env}"
}
