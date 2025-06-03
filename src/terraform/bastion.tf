
data "oci_core_instance" "starter_bastion" {
  instance_id = oci_core_instance.starter_compute.id
}

output "bastion_public_ip" {
  value = data.oci_core_instance.starter_bastion.public_ip
}