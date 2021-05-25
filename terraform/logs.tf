resource "aws_cloudwatch_log_group" "logs" {
  name = "${var.prefix}-logs"

}