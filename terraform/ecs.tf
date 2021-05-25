resource "aws_ecs_task_definition" "bigip-ecs-ctlr" {
  family                   = "${var.prefix}-bigip-ecs-ctlr"
  requires_compatibilities = ["EXTERNAL"]
  network_mode             = "bridge"
  execution_role_arn       = aws_iam_role.task-execution-role.arn
  task_role_arn            = aws_iam_role.task-role.arn

  container_definitions = jsonencode([
    {
      "name" : "bigip-ecs-ctlr",
      "image" : var.bigip_ecs_ctlr,
      "memory" : 256,
      "cpu" : 256,
      "essential" : true,
      "secrets" : [
        {
          "valueFrom" : aws_secretsmanager_secret.bigip_password.id,
          "name" : "F5_PASSWORD"
        }
      ],
      "environment" : [
        {
          "name" : "AWS_DEFAULT_REGION",
          "value" : var.region
        },
        {
          "name" : "BIGIP_URLS",
          "value" : var.bigip_urls
        },
        {
          "name" : "TENANT",
          "value" : var.bigip_tenant
        },
        {
          "name" : "CLUSTER_NAME",
          "value" : var.ecs_cluster
        },
        {
          "name" : "SQS_URL",
          "value" : aws_sqs_queue.ecs_queue.id,
        }
      ],
      "logConfiguration" : {
        "logDriver" : "awslogs",
        "options" : {
          "awslogs-group" : aws_cloudwatch_log_group.logs.name,
          "awslogs-region" : var.region,
          "awslogs-stream-prefix" : "logs"
        }
      }
    }
  ])
}

# resource "aws_ecs_service" "bigip-ecs-ctlr" {
#   name            = "${var.prefix}-bigip-ecs-ctlr"
#   cluster         = var.ecs_cluster
#   task_definition = aws_ecs_task_definition.bigip-ecs-ctlr.arn
#   desired_count   = 1
#   launch_type     = "external"
# }