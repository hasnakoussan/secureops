resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "Security group for SecureOps RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "PostgreSQL from VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "PostgreSQL responses within the VPC only -- RDS never needs to initiate outbound internet traffic"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}
