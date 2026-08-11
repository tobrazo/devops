########################################
# outputs.tf
########################################

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.windows.id
}

output "public_ip" {
  description = "Elastic IP — use this for RDP"
  value       = aws_eip.windows.public_ip
}

output "rdp_connection" {
  description = "mstsc target (IP:port)"
  value       = "${aws_eip.windows.public_ip}:3389"
}

output "ami_used" {
  description = "Windows Server 2022 AMI that was deployed"
  value       = data.aws_ami.windows_2022.id
}
