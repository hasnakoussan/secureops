# eks.tf — cluster EKS et son node group.
#
# Compromis de cout assumes pour ce portfolio :
#   - 1 seul noeud EC2 (pas de haute disponibilite)
#   - instance t3.small, la plus economique tout en restant viable
resource "aws_eks_cluster" "main" { # nosemgrep: terraform.lang.security.eks-public-endpoint-enabled.eks-public-endpoint-enabled -- Acces public restreint a l'IP admin (/32, voir public_access_cidrs), pas ouvert a Internet. Pas de VPN/bastion en place.
  #checkov:skip=CKV_AWS_39:Public access restricted to admin IP via public_access_cidrs (/32), not fully disabled -- no VPN/bastion in place to administer the cluster otherwise.
  #checkov:skip=CKV_AWS_58:KMS envelope encryption for Kubernetes secrets not enabled -- cost/complexity not justified for this portfolio. Sensitive app secrets (DB, JWT, RabbitMQ) go through Secrets Manager + External Secrets Operator, not stored in plain K8s secrets.
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
    public_access_cidrs     = ["160.176.148.185/32"]
  }
  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]
  tags = {
    Name = "${var.project_name}-cluster"
  }
}

resource "aws_cloudwatch_log_group" "eks_cluster" {
  #checkov:skip=CKV_AWS_158:KMS encryption not enabled for this log group -- default AES256 encryption judged sufficient for this portfolio.
  #checkov:skip=CKV_AWS_338:1 year retention not applied -- 7 days retention chosen to limit CloudWatch costs on this portfolio project.
  name              = "/aws/eks/${var.project_name}-cluster/cluster"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-eks-logs"
  }
}

# Launch template personnalisé, uniquement pour augmenter max-pods via
# nodeadm (AL2023). ENABLE_PREFIX_DELEGATION=true est déjà actif sur le CNI,
# mais kubelet calcule sa propre limite de pods au démarrage et l'ignore par
# défaut -- ce NodeConfig force la vraie valeur (110, standard AWS pour une
# instance avec prefix delegation). Format MIME multipart requis par EKS
# pour un nodegroup managé (il fusionne ce user_data avec son propre script
# de bootstrap).
resource "aws_launch_template" "eks_nodes" {
  name_prefix = "${var.project_name}-nodes-"

  user_data = base64encode(<<-EOT
    MIME-Version: 1.0
    Content-Type: multipart/mixed; boundary="BOUNDARY"

    --BOUNDARY
    Content-Type: application/node.eks.aws

    ---
    apiVersion: node.eks.aws/v1alpha1
    kind: NodeConfig
    spec:
      kubelet:
        config:
          maxPods: 110

    --BOUNDARY--
  EOT
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${var.project_name}-nodes"
    }
  }
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-nodes"
  node_role_arn   = aws_iam_role.eks_node.arn
  subnet_ids      = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  instance_types  = ["t3.small"]
  ami_type        = "AL2023_x86_64_STANDARD"
  capacity_type   = "ON_DEMAND"

  launch_template {
    id      = aws_launch_template.eks_nodes.id
    version = aws_launch_template.eks_nodes.latest_version
  }

  scaling_config {
    desired_size = 4
    min_size     = 3
    max_size     = 4
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
  depends_on   = [aws_eks_node_group.main]
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
