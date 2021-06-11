provider "aws" {
  region = var.aws_region
}


resource "aws_vpc" "f5-volterra-vpc" {
  cidr_block           = "10.0.0.0/16"
  instance_tenancy     = "default"
  enable_dns_support   = "true"
  enable_dns_hostnames = "true"
  enable_classiclink   = "false"

  tags = {
    Name = "${var.prefix}-f5-volterra-vpc"
  }
}

resource "aws_subnet" "f5-volterra-external" {
  vpc_id                  = aws_vpc.f5-volterra-vpc.id
  cidr_block              = "10.0.0.0/24"
  map_public_ip_on_launch = "true"
  availability_zone       = "${var.aws_region}${var.az1}"

  tags = {
    Name = "${var.prefix}-f5-volterra-external"
  }
}


resource "aws_subnet" "f5-volterra-internal" {
  vpc_id                  = aws_vpc.f5-volterra-vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = "false"
  availability_zone       = "${var.aws_region}${var.az1}"

  tags = {
    Name = "${var.prefix}-f5-volterra-internal"
  }
}


resource "aws_subnet" "f5-volterra-workload" {
  vpc_id                  = aws_vpc.f5-volterra-vpc.id
  cidr_block              = "10.0.2.0/24"
  map_public_ip_on_launch = "false"
  availability_zone       = "${var.aws_region}${var.az1}"

  tags = {
    Name = "${var.prefix}-f5-volterra-workload"
  }
}

resource "aws_internet_gateway" "f5-volterra-vpc-gw" {
  vpc_id = aws_vpc.f5-volterra-vpc.id

  tags = {
    Name = "${var.prefix}-f5-volterra-igw"
  }
}

resource "aws_route_table" "f5-volterra-vpc-external-rt" {
  vpc_id = aws_vpc.f5-volterra-vpc.id

  tags = {
    Name = "${var.prefix}-f5-volterra-external-rt"
  }
}

resource "aws_route" "volterra-gateway" {
  route_table_id         = aws_route_table.f5-volterra-vpc-external-rt.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.f5-volterra-vpc-gw.id
  depends_on             = [aws_route_table.f5-volterra-vpc-external-rt]
}

resource "aws_route_table_association" "f5-volterra-external" {
  subnet_id      = aws_subnet.f5-volterra-external.id
  route_table_id = aws_route_table.f5-volterra-vpc-external-rt.id
}

resource "aws_security_group" "volterra-vpc" {
  name   = "${var.prefix}-f5-volterra-vpc"
  vpc_id = aws_vpc.f5-volterra-vpc.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["10.0.0.0/16"]
  }

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["192.168.0.0/16"]
  }

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.trusted_ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_network_acls" "udf_acl" {
  vpc_id = aws_vpc.f5-volterra-vpc.id
}
resource "aws_network_acl_rule" "tcp_53" {
  network_acl_id = aws_vpc.f5-volterra-vpc.default_network_acl_id
  rule_number    = 90
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "10.0.0.0/8"
  from_port      = 53
  to_port        = 53
}

resource "aws_network_acl_rule" "udp_53" {
  network_acl_id = aws_vpc.f5-volterra-vpc.default_network_acl_id
  rule_number    = 91
  egress         = false
  protocol       = "udp"
  rule_action    = "allow"
  cidr_block     = "10.0.0.0/8"
  from_port      = 53
  to_port        = 53
}

resource "aws_network_acl_rule" "deny_tcp_53" {
  network_acl_id = aws_vpc.f5-volterra-vpc.default_network_acl_id
  rule_number    = 98
  egress         = false
  protocol       = "tcp"
  rule_action    = "deny"
  cidr_block     = "0.0.0.0/0"
  from_port      = 53
  to_port        = 53
}

resource "aws_network_acl_rule" "deny_udp_53" {
  network_acl_id = aws_vpc.f5-volterra-vpc.default_network_acl_id
  rule_number    = 99
  egress         = false
  protocol       = "udp"
  rule_action    = "deny"
  cidr_block     = "0.0.0.0/0"
  from_port      = 53
  to_port        = 53
}