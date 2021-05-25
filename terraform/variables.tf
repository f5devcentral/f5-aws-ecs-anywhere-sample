variable "prefix" {
  description = "prefix for resources created"
  default     = "ecs-anywhere-f5-demo"
}
variable "region" {
  description = "AWS region"
  default     = "us-east-1"
}
variable "bigip_password" {
  description = "Password for BIG-IP"
}
variable "ecs_cluster" {
  description = "Name of ECS Anywhere cluster"
}
variable "account_id" {
  default = ""
}
variable "bigip_tenant" {
  description = "Tenant/Partition for ECS config on BIG-IP"
}
variable "bigip_urls" {
  description = "URL(s) to BIG-IP (comma separated)"
}
variable "bigip_ecs_ctlr" {
  description = "BIG-IP ECS Controller image location"
}