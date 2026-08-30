provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "secureops"
      Environment = "dev"
      Owner       = "hasna"
      ManagedBy   = "terraform"
    }
  }
}
