output "efs_id" {
  value       = aws_efs_file_system.this.id
  description = "EFS FileSystem ID"
}

output "security_group_id" {
  value       = aws_security_group.efs.id
  description = "EFS security group ID"
}

output "mount_target_ids" {
  value       = [for mt in aws_efs_mount_target.this : mt.id]
  description = "EFS Mount Target IDs"
}
