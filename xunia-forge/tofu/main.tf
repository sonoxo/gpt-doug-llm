terraform {
  required_version = ">= 1.7.0"
}

variable "project_dir" {
  type        = string
  description = "Absolute XUNIA Forge directory"
}

resource "terraform_data" "forge" {
  triggers_replace = [filesha256("${var.project_dir}/compose.yaml")]
  provisioner "local-exec" {
    command = "docker compose --project-directory ${var.project_dir} up -d --build"
  }
  provisioner "local-exec" {
    when    = destroy
    command = "docker compose --project-directory ${self.input} down"
  }
  input = var.project_dir
}

output "dashboard" { value = "http://127.0.0.1:8787" }
output "gateway" { value = "http://127.0.0.1:4000/v1" }
