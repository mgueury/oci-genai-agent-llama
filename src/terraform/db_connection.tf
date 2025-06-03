// -- Vault -----------------------------------------------------------------

resource "oci_kms_vault" "starter_kms_vault" {
  compartment_id = local.lz_db_cmp_ocid
  display_name ="${var.prefix}-vault"
  vault_type   = "DEFAULT"
}

resource "time_sleep" "vault_session_wait" {
  depends_on = [ oci_kms_vault.starter_kms_vault ]
  create_duration = "30s"
}

// -- Kms -------------------------------------------------------------------

resource "oci_kms_key" "starter_kms_key" {
  depends_on = [ time_sleep.vault_session_wait ]

  #Required
  compartment_id      = local.lz_db_cmp_ocid
  display_name        = "${var.prefix}-key"
  management_endpoint = oci_kms_vault.starter_kms_vault.management_endpoint
  protection_mode     = "SOFTWARE"

  key_shape {
    #Required
    algorithm = "AES"
    length    = 32
  }
}

// -- Secret ----------------------------------------------------------------

resource "oci_vault_secret" "starter_secret_atp" {
  #Required
  compartment_id = local.lz_db_cmp_ocid
  secret_content {
    #Required
    content_type = "BASE64"

    #Optional
    content = base64encode(var.db_password)
    name    = "name"
    stage   = "CURRENT"
  }
  key_id      = oci_kms_key.starter_kms_key.id
  secret_name = "atp-password"
  vault_id    = oci_kms_vault.starter_kms_vault.id
}

// -- Database Tools ----------------------------------------------------------

data "oci_database_tools_database_tools_endpoint_services" "starter_database_tools_endpoint_services" {
  compartment_id = var.compartment_ocid
  state = "ACTIVE"
}

data "oci_database_tools_database_tools_endpoint_service" "starter_database_tools_endpoint_service" {
  database_tools_endpoint_service_id = data.oci_database_tools_database_tools_endpoint_services.starter_database_tools_endpoint_services.database_tools_endpoint_service_collection.0.items.0.id
}

// -- Private Endpoint  -----------------------------------------------------

resource "oci_database_tools_database_tools_private_endpoint" "starter_database_tools_private_endpoint" {
  #Required
  compartment_id      = local.lz_db_cmp_ocid
  display_name        = "${var.prefix}-dbtools-private-endpoint"
  endpoint_service_id = data.oci_database_tools_database_tools_endpoint_service.starter_database_tools_endpoint_service.id
  subnet_id           = oci_core_subnet.starter_db_subnet.id

  #Optional
  description         = "Private Endpoint to ATP"
}

data "oci_database_tools_database_tools_private_endpoints" "starter_database_tools_private_endpoints" {
  compartment_id  = local.lz_db_cmp_ocid
  state           = "ACTIVE"
  subnet_id       = oci_core_subnet.starter_db_subnet.id
  display_name    = oci_database_tools_database_tools_private_endpoint.starter_database_tools_private_endpoint.display_name
}

output "private_endpoints_d" {
  value = data.oci_database_tools_database_tools_private_endpoints.starter_database_tools_private_endpoints
}

data "oci_database_tools_database_tools_private_endpoint" "starter_database_tools_private_endpoint" {
  database_tools_private_endpoint_id = data.oci_database_tools_database_tools_private_endpoints.starter_database_tools_private_endpoints.database_tools_private_endpoint_collection.0.items.0.id
}

output "private_endpoint_d" {
  value = data.oci_database_tools_database_tools_private_endpoint.starter_database_tools_private_endpoint
}

// -- Connection ------------------------------------------------------------

# Connection - Resource
resource "oci_database_tools_database_tools_connection" "starter_dbtools_connection" {
  compartment_id    = local.lz_db_cmp_ocid
  display_name      = "${var.prefix}-dbtools-connection"
  type              = "ORACLE_DATABASE"
  connection_string = local.db_url
  user_name         = "admin"
  user_password {
    value_type = "SECRETID"
    # The user password to use exists as a secret in an OCI Vault
    secret_id  = oci_vault_secret.starter_secret_atp.id
  }

  # Optional
  advanced_properties = {
    "oracle.jdbc.loginTimeout": "0"
  }
  related_resource {
    entity_type = "DATABASE"
    identifier  = oci_database_autonomous_database.starter_atp.id
  }
  private_endpoint_id = oci_database_tools_database_tools_private_endpoint.starter_database_tools_private_endpoint.id
}

output "connection_r" {
  value = oci_database_tools_database_tools_connection.starter_dbtools_connection
}

# Connection - Data Sources
data "oci_database_tools_database_tools_connections" "starter_database_tools_connections" {
  compartment_id = local.lz_db_cmp_ocid
  display_name   = oci_database_tools_database_tools_connection.starter_dbtools_connection.display_name
  state          = "ACTIVE"
}

output "connections_d" {
  value = data.oci_database_tools_database_tools_connections.starter_database_tools_connections
}
