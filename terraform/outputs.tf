output "sqs_url" {
  value = aws_sqs_queue.ecs_queue.id
}