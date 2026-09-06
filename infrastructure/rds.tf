resource "aws_db_subnet_group" "postgres" {
  name = "${var.project_name}-postgres-subnet-group"
  subnet_ids = [
    aws_subnet.private_a.id,
    aws_subnet.private_b.id
  ]
  tags = {
    Name = "${var.project_name}-postgres-subnet-group"
  }
}
resource "aws_db_instance" "postgres" {
  #checkov:skip=CKV_AWS_161:IAM authentication not used -- this project relies on password auth via Secrets Manager + External Secrets Operator, consistent across the whole stack.
  #checkov:skip=CKV_AWS_293:deletion_protection intentionally false -- allows easy terraform destroy for this portfolio project.
  #checkov:skip=CKV_AWS_118:Enhanced monitoring not enabled -- additional CloudWatch cost not justified for this portfolio.
  #checkov:skip=CKV_AWS_157:Multi-AZ not enabled -- would double RDS cost, not justified for a portfolio without real HA requirement.
  #checkov:skip=CKV_AWS_354:Performance Insights uses default AWS-managed encryption -- dedicated KMS CMK not justified for this portfolio.
  #checkov:skip=CKV2_AWS_30:Query logging (log_statement) not enabled -- would require a dedicated parameter group, additional CloudWatch log volume/cost not justified for this low-traffic portfolio.
  identifier = "${var.project_name}-postgres"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro"
  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true
  db_name  = "secureops_auth_db"
  username = var.db_username
  password = random_password.database.result
  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible = false
  multi_az = false
  backup_retention_period = 1
  skip_final_snapshot = true
  deletion_protection = false
  copy_tags_to_snapshot = true
  auto_minor_version_upgrade = true
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  tags = {
    Name = "${var.project_name}-postgres"
  }
}
