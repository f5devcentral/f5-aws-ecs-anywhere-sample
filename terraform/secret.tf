resource "aws_secretsmanager_secret" "bigip_password" {
  name = "${var.prefix}-bigip_password"
}
resource "aws_secretsmanager_secret_version" "bigip_password" {
  secret_id     = aws_secretsmanager_secret.bigip_password.id
  secret_string = var.bigip_password
}