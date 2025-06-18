#!/bin/bash
# Environment Variables
export TF_VAR_prefix="llama"

export TF_VAR_ui_type="html"
export TF_VAR_db_type="autonomous"
export TF_VAR_license_model="__TO_FILL__"
export TF_VAR_deploy_type="public_compute"
export TF_VAR_language="python"
export TF_VAR_db_user="admin"

export TF_VAR_compartment_ocid="__TO_FILL__"
# TF_VAR_db_password : Min length 12 characters, 2 lowercase, 2 uppercase, 2 numbers, 2 special characters. Ex: LiveLab__12345
export TF_VAR_db_password="__TO_FILL__"
export TF_VAR_vault_ocid="__TO_FILL__"
export TF_VAR_vault_key_ocid="__TO_FILL__"

if [ -f $HOME/.oci_starter_profile ]; then
  . $HOME/.oci_starter_profile
fi

# Creation Details
export OCI_STARTER_CREATION_DATE=2025-06-03-11-37-08-044670
export OCI_STARTER_VERSION=3.7
export OCI_STARTER_PARAMS="prefix,java_framework,java_vm,java_version,ui_type,db_type,license_model,mode,infra_as_code,db_password,oke_type,security,deploy_type,language"

