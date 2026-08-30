output "eks_cluster_name" {
  description = "Nom du cluster EKS"
  value       = aws_eks_cluster.main.name
}

output "eks_cluster_endpoint" {
  description = "Endpoint de l'API Kubernetes"
  value       = aws_eks_cluster.main.endpoint
}

output "eks_cluster_certificate_authority" {
  description = "Certificat d'autorité du cluster, nécessaire pour configurer kubectl"
  value       = aws_eks_cluster.main.certificate_authority[0].data
}
