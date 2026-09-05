# ============================================================
# ECR repositories
# ============================================================

#checkov:skip=CKV_AWS_51:Tags mutables volontairement conservés -- le tag ':latest' est réutilisé à chaque build par le pipeline CI et référencé par les manifests K8s actuels. Passage aux tags immuables prévu lors de la mise en place du CD (Argo CD), qui déploiera par digest/SHA plutôt que par tag réutilisé.
#checkov:skip=CKV_AWS_136:Chiffrement KMS non activé -- chiffrement AES256 par défaut jugé suffisant pour ce portfolio, coût/complexité additionnels d'une clé KMS dédiée non justifiés.
resource "aws_ecr_repository" "auth" {
  name                 = "${var.project_name}/auth"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-auth"
  }
}

#checkov:skip=CKV_AWS_51:Tags mutables volontairement conservés -- voir justification sur le repo auth ci-dessus.
#checkov:skip=CKV_AWS_136:Chiffrement KMS non activé -- voir justification sur le repo auth ci-dessus.
resource "aws_ecr_repository" "scan" {
  name                 = "${var.project_name}/scan"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-scan"
  }
}

#checkov:skip=CKV_AWS_51:Tags mutables volontairement conservés -- voir justification sur le repo auth ci-dessus.
#checkov:skip=CKV_AWS_136:Chiffrement KMS non activé -- voir justification sur le repo auth ci-dessus.
resource "aws_ecr_repository" "worker" {
  name                 = "${var.project_name}/worker"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-worker"
  }
}

#checkov:skip=CKV_AWS_51:Tags mutables volontairement conservés -- voir justification sur le repo auth ci-dessus.
#checkov:skip=CKV_AWS_136:Chiffrement KMS non activé -- voir justification sur le repo auth ci-dessus.
resource "aws_ecr_repository" "dashboard" {
  name                 = "${var.project_name}/dashboard"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-dashboard"
  }
}


# ============================================================
# ECR Lifecycle Policies
# Keep only the 10 most recent images
# ============================================================

resource "aws_ecr_lifecycle_policy" "auth" {
  repository = aws_ecr_repository.auth.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 10 images"

        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }

        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "scan" {
  repository = aws_ecr_repository.scan.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 10 images"

        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }

        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "worker" {
  repository = aws_ecr_repository.worker.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 10 images"

        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }

        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "dashboard" {
  repository = aws_ecr_repository.dashboard.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 10 images"

        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }

        action = {
          type = "expire"
        }
      }
    ]
  })
}
