resource "aws_sqs_queue" "ecs_queue" {
  name = "${var.prefix}-queue"

}