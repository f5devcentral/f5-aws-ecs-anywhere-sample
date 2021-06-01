resource "random_id" "id" {
  byte_length = 2
}
resource "aws_secretsmanager_secret" "bigip_password" {
  name = format("%s-bigip-password-%s", var.prefix, random_id.id.hex)
}

resource "aws_secretsmanager_secret_version" "bigip_password" {
  secret_id     = aws_secretsmanager_secret.bigip_password.id
  secret_string = var.bigip_password
}