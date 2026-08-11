resource "aws_iam_role" "admin" {
  name = var.role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = var.trusted_account_arn
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = {
    Name = var.role_name
  }
}
