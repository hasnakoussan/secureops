# ============================================================
# DATABASE SECRET
# ============================================================
resource "aws_secretsmanager_secret" "database" {
  #checkov:skip=CKV_AWS_149:Dedicated KMS CMK not used -- default AWS-managed encryption judged sufficient for this portfolio.
  #checkov:skip=CKV2_AWS_57:Automatic rotation not enabled -- would require a dedicated rotation Lambda for RDS; out of scope for this portfolio, deferred as future improvement.
  name        = "${var.project_name}/database"
  description = "SecureOps PostgreSQL credentials"
  tags = {
    Name = "${var.project_name}-database-secret"
  }
}
resource "random_password" "database" {
  length  = 64
  special = false
}
resource "aws_secretsmanager_secret_version" "database" {
  secret_id = aws_secretsmanager_secret.database.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.database.result
  })
}
# ============================================================
# JWT SECRET
# ============================================================
resource "aws_secretsmanager_secret" "jwt" {
  #checkov:skip=CKV_AWS_149:Dedicated KMS CMK not used -- default AWS-managed encryption judged sufficient for this portfolio.
  #checkov:skip=CKV2_AWS_57:Automatic rotation not enabled -- would require app-level logic to reload pods on rotation; out of scope for this portfolio, deferred as future improvement.
  name        = "${var.project_name}/jwt"
  description = "SecureOps JWT secret"
  tags = {
    Name = "${var.project_name}-jwt-secret"
  }
}
resource "random_password" "jwt" {
  length  = 64
  special = false
}
resource "aws_secretsmanager_secret_version" "jwt" {
  secret_id     = aws_secretsmanager_secret.jwt.id
  secret_string = random_password.jwt.result
}
# ============================================================
# RABBITMQ SECRET
# ============================================================
resource "aws_secretsmanager_secret" "rabbitmq" {
  #checkov:skip=CKV_AWS_149:Dedicated KMS CMK not used -- default AWS-managed encryption judged sufficient for this portfolio.
  #checkov:skip=CKV2_AWS_57:Automatic rotation not enabled -- would require app-level logic to reload pods on rotation; out of scope for this portfolio, deferred as future improvement.
  name        = "${var.project_name}/rabbitmq"
  description = "SecureOps RabbitMQ credentials"
  tags = {
    Name = "${var.project_name}-rabbitmq-secret"
  }
}
resource "random_password" "rabbitmq" {
  length  = 32
  special = false
}
resource "aws_secretsmanager_secret_version" "rabbitmq" {
  secret_id     = aws_secretsmanager_secret.rabbitmq.id
  secret_string = random_password.rabbitmq.result
}
