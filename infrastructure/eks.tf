# eks.tf — cluster EKS et son node group.
#
# Compromis de coût assumés pour ce portfolio :
#   - 1 seul nœud EC2 (pas de haute disponibilité)
#   - instance t3.small, la plus économique tout en restant viable
#   - accès public à l'API Kubernetes ouvert à 0.0.0.0/0 : plus simple à
#     piloter depuis n'importe où, mais surface d'attaque plus large
#     qu'une vraie prod ne tolérerait. L'authentification IAM reste
#     requise pour toute action réelle sur le cluster.

resource "aws_eks_cluster" "main" {
  name     = "${var.project_name}-cluster"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.30"

  vpc_config {
    subnet_ids = concat(
      [aws_subnet.public_a.id, aws_subnet.public_b.id],
      [aws_subnet.private_a.id, aws_subnet.private_b.id],
    )
    endpoint_public_access  = true
    endpoint_private_access = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-nodes"
  node_role_arn   = aws_iam_role.eks_node.arn

  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  instance_types = ["t3.small"]
  ami_type       = "AL2_x86_64"
  capacity_type  = "ON_DEMAND"

  scaling_config {
    desired_size = 1
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
