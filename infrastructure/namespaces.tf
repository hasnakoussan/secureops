resource "kubectl_manifest" "namespace_secureops" {
  yaml_body = <<-YAML
    apiVersion: v1
    kind: Namespace
    metadata:
      name: secureops
  YAML
}
