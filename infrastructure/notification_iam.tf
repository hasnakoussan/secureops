resource "aws_iam_policy" "notification_ses" {
  name        = "${var.project_name}-notification-ses-policy"
  description = "Permissions pour le Notification Service : envoi d'emails via SES"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ses:FromAddress" = "secureopsalerts@gmail.com"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role" "notification" {
  name = "${var.project_name}-notification-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "pods.eks.amazonaws.com"
        }
        Action = [
          "sts:AssumeRole",
          "sts:TagSession"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "notification" {
  role       = aws_iam_role.notification.name
  policy_arn = aws_iam_policy.notification_ses.arn
}

resource "aws_eks_pod_identity_association" "notification" {
  cluster_name    = aws_eks_cluster.main.name
  namespace       = "secureops"
  service_account = "notification-sa"
  role_arn        = aws_iam_role.notification.arn

  depends_on = [aws_eks_addon.pod_identity_agent]
}
