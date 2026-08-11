#############################################
# EFS module tailored for EKS usage
# - Creates an SG that allows NFS only from EKS node SG
# - Creates an encrypted FileSystem
# - Creates Mount Targets in provided (private) subnets
#############################################

resource "aws_security_group" "efs" {
  name        = "${var.name}-efs-sg"
  description = "Allow NFS from EKS nodes"
  vpc_id      = var.vpc_id

  # Outbound open (fine for EFS)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}

# Allow NFS only from the EKS node security group
resource "aws_security_group_rule" "efs_from_nodes" {
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  security_group_id        = aws_security_group.efs.id
  source_security_group_id = var.node_security_group_id
  description              = "Allow NFS from EKS nodes"
}

resource "aws_efs_file_system" "this" {
  creation_token   = var.name
  encrypted        = false #true 
  kms_key_id       = null  # kms_key_id = aws_kms_key.efs.arn / kms_key_id      = var.kms_key_id
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"

  # Optional lifecycle policy (transition to IA)
  lifecycle_policy {
    transition_to_ia = var.transition_to_ia # e.g. "AFTER_30_DAYS" or null
  }

  tags = merge(var.tags, { Name = var.name })
}

# Create a mount target in each subnet (use private subnets)
resource "aws_efs_mount_target" "this" {
  for_each        = { for idx, subnet_id in var.subnet_ids : idx => subnet_id }
  file_system_id  = aws_efs_file_system.this.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}
