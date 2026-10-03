variable "aws_region" {
  description = "AWS region where SecureOps infrastructure will be deployed"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the SecureOps VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "project_name" {
  description = "the project name"
  type        = string
  default     = "secureops"
}
variable "availability_zones" {
  description = "Availability Zones used by SecureOps"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}
variable "db_username" {
  description = "Master username for PostgreSQL"
  type        = string
  sensitive   = true
  default     = "secureops_admin"
}

variable "slack_webhook_url" {
  description = "Slack Incoming Webhook URL for SecureOps notifications"
  type        = string
  sensitive   = true
}
variable "rds_extra_availability_zone" {
  description = "Extra AZ for the RDS subnet group (capacity for db.t4g.micro + gp3)"
  type        = string
  default     = "us-east-1f"
}
