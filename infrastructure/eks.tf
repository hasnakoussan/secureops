# eks.tf — cluster EKS et son node group.
#
# Compromis de coût assumés pour ce portfolio :
#   - 1 seul nœud EC2 (pas de haute disponibilité)
#   - instance t3.small, la plus économique tout en restant viable

#checkov:skip=CKV_AWS_58:Chiffrement KMS des secrets Kubernetes non activé -- coût/complexité additionnels non justifiés pour ce portfolio. Les secrets applicatifs sensibles (DB, JWT, RabbitMQ) transitent par AWS Secrets Manager + External Secrets Operator, pas stockés en clair côté EKS.
resource "aws_eks_cluster" "main" { # nosemgrep: terraform.lang.security.eks-public-endpoint-enabled.eks-public-endpoint-enabled -- Accès public restreint à l'IP admin (/32, voir public_access_cidrs L17), pas ouvert à Internet. Pas de VPN/bastion en place.
  name     = "${var.project_name}-cluster"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.34"

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  vpc_config {
    subnet_ids = concat(
      [aws_subnet.public_a.id, aws_subnet.public_b.id],
      [aws_subnet.private_a.id, aws_subnet.private_b.id],
    )
    endpoint_public_access  = true
    endpoint_private_access = true
    public_access_cidrs     = ["41.251.11.164/32"]
  }
  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]
  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# Groupe de logs CloudWatch dédié, avec rétention courte pour limiter les coûts
# (sans ce bloc, EKS créerait le groupe avec une rétention illimitée par défaut)
resource "aws_cloudwatch_log_group" "eks_cluster" {
  name              = "/aws/eks/${var.project_name}-cluster/cluster"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-eks-logs"
  }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-nodes"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  instance_types = ["t3.small"]
  ami_type       = "AL2023_x86_64_STANDARD"
  capacity_type  = "ON_DEMAND"
  scaling_config {
    desired_size = 2
    min_size     = 1
    max_size     = 2
  }
  update_config {
    max_unavailable = 1
  }
  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_ecr_pull,
  ]
  tags = {
    Name = "${var.project_name}-nodes"
  }
}
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "vpc-cni"
}
resource "aws_eks_addon" "coredns" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "coredns"
  depends_on = [aws_eks_node_group.main]
}
resource "aws_eks_addon" "kube_proxy" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "kube-proxy"
}
resource "aws_eks_addon" "pod_identity_agent" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "eks-pod-identity-agent"
  depends_on = [
    aws_eks_node_group.main
  ]
}
