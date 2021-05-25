# Terraform Resources

This directory contains Terraform resources that can be used to
provide a working environment for the BIG-IP ECS Controller.

Sample terraform.tfvars file.

```
bigip_password = "[Password]"
ecs_cluster    = "chen-ecs-anywhere"
bigip_tenant   = "EcsAnywhere"
bigip_url      = "https://192.168.1.200"
bigip_ecs_ctlr = "123456.dkr.ecr.us-east-1.amazonaws.com/bigip-ecs-ctlr:latest"
```

### Secret

BIG-IP Password

### SQS

Queue for ECS events

### Logs

Log group used for output from controller

### EventBridge

Rule to send ECS events to SQS

### IAM

taskRole/taskExecution

### ECS

Task definition
