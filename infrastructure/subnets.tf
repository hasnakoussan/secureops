resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = var.availability_zones[0]
  map_public_ip_on_launch = true

  tags = {
    Name                                      = "secureops-public-a"
    Tier                                      = "public"
    "kubernetes.io/role/elb"                  = "1"
    "kubernetes.io/cluster/secureops-cluster" = "shared"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = var.availability_zones[1]
  map_public_ip_on_launch = true

  tags = {
    Name                                      = "secureops-public-b"
    Tier                                      = "public"
    "kubernetes.io/role/elb"                  = "1"
    "kubernetes.io/cluster/secureops-cluster" = "shared"
  }
}
# ── IGW-creation ──────────────────────────

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project_name}-igw" }
}
# ── Route table publique ──────────────────────────
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "${var.project_name}-public-rt" }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}





# ── privates subnets  ──────────────────────────
resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = var.availability_zones[0]

  tags = {
    Name                                      = "secureops-private-a"
    Tier                                      = "private"
    "kubernetes.io/role/internal-elb"         = "1"
    "kubernetes.io/cluster/secureops-cluster" = "shared"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.12.0/24"
  availability_zone = var.availability_zones[1]

  tags = {
    Name                                      = "secureops-private-b"
    Tier                                      = "private"
    "kubernetes.io/role/internal-elb"         = "1"
    "kubernetes.io/cluster/secureops-cluster" = "shared"
  }
}
