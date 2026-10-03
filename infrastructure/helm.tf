resource "helm_release" "aws_load_balancer_controller" {
  name       = "aws-load-balancer-controller"
  namespace  = "kube-system"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"

  set {
    name  = "clusterName"
    value = aws_eks_cluster.main.name
  }

  set {
    name  = "serviceAccount.create"
    value = "true"
  }

  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }

  depends_on = [
    aws_eks_addon.pod_identity_agent,
    aws_eks_pod_identity_association.lb_controller
  ]
}
resource "helm_release" "external_secrets" {
  name       = "external-secrets"
  namespace  = "external-secrets"
  repository = "https://charts.external-secrets.io"
  chart      = "external-secrets"

  create_namespace = true

  set {
    name  = "serviceAccount.create"
    value = "true"
  }

  set {
    name  = "serviceAccount.name"
    value = "external-secrets"
  }

  depends_on = [
    aws_eks_addon.pod_identity_agent,
    aws_eks_pod_identity_association.external_secrets
  ]
}
resource "helm_release" "argocd" {
  name      = "argocd"
  namespace = "argocd"

  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"

  create_namespace = true

  set {
    name  = "server.service.type"
    value = "ClusterIP"
  }

  depends_on = [
    aws_eks_node_group.main
  ]
}

resource "helm_release" "descheduler" {
  name       = "descheduler"
  namespace  = "kube-system"
  repository = "https://kubernetes-sigs.github.io/descheduler/"
  chart      = "descheduler"
  version    = "0.36.0"

  values = [
    file("${path.module}/values-descheduler.yaml")
  ]

  depends_on = [
    aws_eks_node_group.main
  ]
}

