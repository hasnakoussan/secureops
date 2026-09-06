# ── VPC ──────────────────────────────────────────
resource "aws_vpc" "main" {
  #checkov:skip=CKV2_AWS_11:VPC Flow Logs not enabled -- ongoing CloudWatch cost not justified for this portfolio project.
  #checkov:skip=CKV2_AWS_12:Default security group left as-is -- no resources attached to it (all resources use dedicated security groups), residual risk minimal.
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = "${var.project_name}-vpc" }
}
