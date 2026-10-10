# ============================================================
# ECR repositories
# ============================================================

resource "aws_ecr_repository" "auth" {
  #checkov:skip=CKV_AWS_51:Mutable tag latest is intentional, used by CI pipeline and K8s manifests. Will move to immutable tags with Argo CD (deploy by SHA).
  #checkov:skip=CKV_AWS_136:AES256 default encryption judged sufficient for this portfolio, no dedicated KMS key.
  name                 = "${var.project_name}/auth"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-auth"
  }
}

resource "aws_ecr_repository" "scan" {
  #checkov:skip=CKV_AWS_51:Mutable tag latest is intentional, used by CI pipeline and K8s manifests. Will move to immutable tags with Argo CD (deploy by SHA).
  #checkov:skip=CKV_AWS_136:AES256 default encryption judged sufficient for this portfolio, no dedicated KMS key.
  name                 = "${var.project_name}/scan"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-scan"
  }
}

resource "aws_ecr_repository" "worker" {
  #checkov:skip=CKV_AWS_51:Mutable tag latest is intentional, used by CI pipeline and K8s manifests. Will move to immutable tags with Argo CD (deploy by SHA).
  #checkov:skip=CKV_AWS_136:AES256 default encryption judged sufficient for this portfolio, no dedicated KMS key.
  name                 = "${var.project_name}/worker"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-worker"
  }
}

resource "aws_ecr_repository" "dashboard" {
  #checkov:skip=CKV_AWS_51:Mutable tag latest is intentional, used by CI pipeline and K8s manifests. Will move to immutable tags with Argo CD (deploy by SHA).
  #checkov:skip=CKV_AWS_136:AES256 default encryption judged sufficient for this portfolio, no dedicated KMS key.
  name                 = "${var.project_name}/dashboard"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-dashboard"
  }
}

resource "aws_ecr_repository" "notification" {
  #checkov:skip=CKV_AWS_51:Mutable tag latest is intentional, used by CI pipeline and K8s manifests. Will move to immutable tags with Argo CD (deploy by SHA).
  #checkov:skip=CKV_AWS_136:AES256 default encryption judged sufficient for this portfolio, no dedicated KMS key.
  name                 = "${var.project_name}/notification"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-notification"
  }
}

resource "aws_ecr_repository" "falco_bridge" {
  #checkov:skip=CKV_AWS_51:Mutable tag latest is intentional, used by CI pipeline and K8s manifests. Will move to immutable tags with Argo CD (deploy by SHA).
  #checkov:skip=CKV_AWS_136:AES256 default encryption judged sufficient for this portfolio, no dedicated KMS key.
  name                 = "${var.project_name}/falco-bridge"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-falco-bridge"
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

resource "aws_ecr_lifecycle_policy" "notification" {
  repository = aws_ecr_repository.notification.name

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

resource "aws_ecr_lifecycle_policy" "falco_bridge" {
  repository = aws_ecr_repository.falco_bridge.name

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

# ============================================================
# ECR repository: response
# ============================================================

resource "aws_ecr_repository" "response" {
  #checkov:skip=CKV_AWS_51:Mutable tag latest is intentional, used by CI pipeline and K8s manifests. Will move to immutable tags with Argo CD (deploy by SHA).
  #checkov:skip=CKV_AWS_136:AES256 default encryption judged sufficient for this portfolio, no dedicated KMS key.
  name                 = "${var.project_name}/response"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-response"
  }
}

resource "aws_ecr_lifecycle_policy" "response" {
  repository = aws_ecr_repository.response.name

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
