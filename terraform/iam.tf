resource "aws_iam_role" "task-execution-role" {
  name               = "${var.prefix}-task-execution-role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

}

resource "aws_iam_role_policy_attachment" "attach-execution" {
  role       = aws_iam_role.task-execution-role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task-role" {
  name               = "${var.prefix}-task-role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

}

# resource "aws_iam_role_policy_attachment" "attach-execution-task" {
#   role       = aws_iam_role.task-role.name
#   policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
# }

resource "aws_iam_role_policy_attachment" "attach-ssm" {
  role       = aws_iam_role.task-role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
}
resource "aws_iam_role_policy" "ecs-read-only" {
  role = aws_iam_role.task-role.name
  policy = jsonencode(
    {
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Sid" : "VisualEditor0",
          "Effect" : "Allow",
          "Action" : [
            "ecs:ListAttributes",
            "ecs:DescribeTaskSets",
            "ecs:DescribeTaskDefinition",
            "ecs:DescribeClusters",
            "ecs:ListServices",
            "ecs:ListAccountSettings",
            "ecs:DescribeCapacityProviders",
            "ecs:ListTagsForResource",
            "ecs:ListTasks",
            "ecs:ListTaskDefinitionFamilies",
            "ecs:DescribeServices",
            "ecs:ListContainerInstances",
            "ecs:DescribeContainerInstances",
            "ecs:DescribeTasks",
            "ecs:ListTaskDefinitions",
            "ecs:ListClusters"
          ],
          "Resource" : "*"
        }
      ]
  })
}

resource "aws_iam_role_policy" "ecs-read-secret" {
  role = aws_iam_role.task-execution-role.name
  policy = jsonencode(
    {
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Effect" : "Allow",
          "Action" : [
            "secretsmanager:GetSecretValue"
          ],
          "Resource" : [
            aws_secretsmanager_secret.bigip_password.id
          ]
        }
      ]
    }
  )
}

resource "aws_iam_role_policy" "ecs-update-sqs-queue" {
  role = aws_iam_role.task-role.name
  policy = jsonencode(
    {
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Sid" : "VisualEditor0",
          "Effect" : "Allow",
          "Action" : [
            "sqs:DeleteMessage",
            "sqs:GetQueueUrl",
            "sqs:ChangeMessageVisibility",
            "sqs:SendMessageBatch",
            "sqs:ReceiveMessage",
            "sqs:SendMessage",
            "sqs:GetQueueAttributes",
            "sqs:ListQueueTags",
            "sqs:ListDeadLetterSourceQueues",
            "sqs:DeleteMessageBatch",
            "sqs:PurgeQueue",
            "sqs:ChangeMessageVisibilityBatch",
            "sqs:SetQueueAttributes"
          ],
          "Resource" : aws_sqs_queue.ecs_queue.arn
        },
        {
          "Sid" : "VisualEditor1",
          "Effect" : "Allow",
          "Action" : "sqs:ListQueues",
          "Resource" : "*"
        }
      ]
  })

}