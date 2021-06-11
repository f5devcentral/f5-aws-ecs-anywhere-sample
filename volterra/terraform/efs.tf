resource "aws_efs_file_system" "volterra" {
  availability_zone_name = "${var.aws_region}${var.az1}"
  tags = {
    Name = "${var.prefix}-volterra"
  }
}
resource "aws_efs_mount_target" "volterra" {
  file_system_id  = aws_efs_file_system.volterra.id
  subnet_id       = aws_subnet.f5-volterra-workload.id
  security_groups = [aws_security_group.volterra-vpc.id]
}