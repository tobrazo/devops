variable "bucket_name" {
  description = "Name for the S3 bucket to store tfstate"
  type        = string
}

variable "lock_table_name" {
  description = "Name for the DynamoDB table to lock tfstate"
  type        = string
}
