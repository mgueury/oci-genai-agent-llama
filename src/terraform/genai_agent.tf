variable "namespace" {}

resource "oci_objectstorage_bucket" "starter_agent_bucket" {
  compartment_id = local.lz_serv_cmp_ocid
  namespace      = var.namespace
  name           = "${var.prefix}-agent-bucket"
  object_events_enabled = true

  freeform_tags = local.freeform_tags
}

# -- Knowledge Base ---------------------------------------------------------

resource "oci_generative_ai_agent_knowledge_base" "starter_agent_kb" {
  #Required
  compartment_id                 = local.lz_serv_cmp_ocid
  index_config  {
    index_config_type = "DEFAULT_INDEX_CONFIG"
    should_enable_hybrid_search   = "true"
  }
  display_name                  = "${var.prefix}-agent-kb"
  description                   = "${var.prefix}-agent-kb"
  freeform_tags = local.freeform_tags
}

# -- DataSource ---------------------------------------------------------

resource "oci_generative_ai_agent_data_source" "starter_agent_ds" {
  compartment_id                 = local.lz_serv_cmp_ocid
  knowledge_base_id              = oci_generative_ai_agent_knowledge_base.starter_agent_kb.id
  data_source_config  {
    data_source_config_type = "OCI_OBJECT_STORAGE"
    object_storage_prefixes {
      bucket = oci_objectstorage_bucket.starter_agent_bucket.name
      namespace = var.namespace
    }
  }
  display_name                  = "${var.prefix}-agent-ds"
  description                   = "${var.prefix}-agent-ds"
  freeform_tags = local.freeform_tags
}

# -- IngestionJob ---------------------------------------------------------

resource "oci_generative_ai_agent_data_ingestion_job" "starter_agent_ingestion_job" {
  #Required
  compartment_id                 = local.lz_serv_cmp_ocid
  data_source_id                 = oci_generative_ai_agent_data_source.starter_agent_ds.id
  display_name                  = "${var.prefix}-agent-ingestion-job"
  description                   = "${var.prefix}-agent-ingestion-job"
  freeform_tags = local.freeform_tags
}

# -- Agent ---------------------------------------------------------

resource "oci_generative_ai_agent_agent" "starter_agent" {
  compartment_id                 = local.lz_serv_cmp_ocid
  display_name                   = "${var.prefix}-agent"
  description                    = "${var.prefix}-agent"
  welcome_message                = "How can I help you ?"
  # knowledge_base_ids = [
  #   oci_generative_ai_agent_knowledge_base.starter_agent_kb.id
  # ]  
  freeform_tags = local.freeform_tags
}

# -- Agent Endpoint ---------------------------------------------------------

resource "oci_generative_ai_agent_agent_endpoint" "starter_agent_endpoint" {
  compartment_id                 = local.lz_serv_cmp_ocid
  agent_id                       = oci_generative_ai_agent_agent.starter_agent.id
  display_name                  = "${var.prefix}-agent-endpoint"
  description                   = "${var.prefix}-agent-endpoint"
  should_enable_citation        = "true"
  should_enable_session         = "true"
  should_enable_trace           = "true"
  content_moderation_config  {
    should_enable_on_input = "false"
    should_enable_on_output = "false"
  }
  session_config              {
    idle_timeout_in_seconds = 3600
  }
  freeform_tags = local.freeform_tags  
}

# -- Policies ----------------------------------------------------------------

variable no_policy {
    default="false"
}

resource "oci_identity_policy" "starter_policy" {
    count          = var.no_policy=="true" ? 0 : 1  
    provider       = oci.home    
    name           = "${var.prefix}-policy"
    description    = "${var.prefix} policy"
    compartment_id = local.lz_serv_cmp_ocid

    statements = [
        "allow any-user to manage generative-ai-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${oci_core_instance.starter_compute.id}'",
        "allow any-user to manage genai-agent-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${oci_core_instance.starter_compute.id}'",
        "allow any-user to manage generative-ai-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${data.oci_database_autonomous_database.starter_atp.autonomous_database_id}'",
        "allow any-user to manage genai-agent-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${data.oci_database_autonomous_database.starter_atp.autonomous_database_id}'",
        "allow any-user to manage database-tools-family in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${oci_generative_ai_agent_agent.starter_agent.id}'",
        "allow any-user to read secret-bundle in compartment id ${local.lz_serv_cmp_ocid} where request.principal.id='${oci_generative_ai_agent_agent.starter_agent.id}'"
    ]
}
