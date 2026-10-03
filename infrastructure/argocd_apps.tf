resource "kubectl_manifest" "argocd_root_app" {
  yaml_body = file("${path.module}/../argocd-apps/root.yaml")

  depends_on = [
    helm_release.argocd
  ]
}
