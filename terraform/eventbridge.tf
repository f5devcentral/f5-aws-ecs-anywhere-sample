resource "aws_cloudwatch_event_rule" "ecs_tasks" {
  name        = "${var.prefix}-ecs-tasks"
  description = "Monitor ECS task changes"

  event_pattern = <<EOF
  {
  "source": ["aws.ecs"],
  "detail-type": ["ECS Task State Change"],
  "detail": {
    "clusterArn": ["arn:aws:ecs:${var.region}:${data.aws_caller_identity.current.account_id}:cluster/${var.ecs_cluster}"]
  }
  }
EOF
}

resource "aws_cloudwatch_event_rule" "ecs_services" {
  name        = "${var.prefix}-ecs-services"
  description = "Monitor ECS service tag changes"

  event_pattern = <<EOF
    {
    "source": ["aws.ecs"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {
      "eventSource": ["ecs.amazonaws.com"],
      "eventName": ["TagResource"],
      "requestParameters": {
        "resourceArn": [{
          "prefix": "arn:aws:ecs:${var.region}:${data.aws_caller_identity.current.account_id}:cluster/${var.ecs_cluster}/"
        }]
      }
    }
  }
EOF
}

resource "aws_cloudwatch_event_target" "ecs_tasks" {
  rule = aws_cloudwatch_event_rule.ecs_tasks.id
  arn  = aws_sqs_queue.ecs_queue.arn
}

resource "aws_cloudwatch_event_target" "ecs_services" {
  rule = aws_cloudwatch_event_rule.ecs_services.id
  arn  = aws_sqs_queue.ecs_queue.arn
}