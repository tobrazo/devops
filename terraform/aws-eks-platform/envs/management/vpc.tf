########################################
# vpc.tf — minimal VPC for management EC2
# CIDR 10.1.0.0/16  (prod uses 10.0.0.0/16 — no overlap)
########################################

resource "aws_vpc" "this" {
  cidr_block           = "10.1.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.tags, { Name = "${local.name_prefix}-vpc" })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.tags, { Name = "${local.name_prefix}-igw" })
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.this.id
  cidr_block              = "10.1.1.0/24"
  availability_zone       = "${var.region}a"
  map_public_ip_on_launch = false # we use Elastic IP instead

  tags = merge(local.tags, { Name = "${local.name_prefix}-public-a" })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.tags, { Name = "${local.name_prefix}-rt-public" })
}

resource "aws_route" "default" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

########################################
# Security Groups
########################################

resource "aws_security_group" "windows" {
  name        = "${local.name_prefix}-windows-sg"
  description = "Allow RDP and PostgreSQL access to the management Windows EC2"
  vpc_id      = aws_vpc.this.id

  tags = merge(local.tags, { Name = "${local.name_prefix}-windows-sg" })
}

# RDP — restrict to your IPs via var.rdp_allowed_cidrs
resource "aws_vpc_security_group_ingress_rule" "rdp" {
  for_each = toset(var.rdp_allowed_cidrs)

  security_group_id = aws_security_group.windows.id
  description       = "RDP"
  from_port         = 3389
  to_port           = 3389
  ip_protocol       = "tcp"
  cidr_ipv4         = each.value
}

# PostgreSQL — only if var.postgres_allowed_cidrs is non-empty
resource "aws_vpc_security_group_ingress_rule" "postgres" {
  for_each = toset(var.postgres_allowed_cidrs)

  security_group_id = aws_security_group.windows.id
  description       = "PostgreSQL"
  from_port         = 5432
  to_port           = 5432
  ip_protocol       = "tcp"
  cidr_ipv4         = each.value
}

# Outbound — full (Windows Update, Chocolatey, etc.)
resource "aws_vpc_security_group_egress_rule" "all_out" {
  security_group_id = aws_security_group.windows.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}
