#!/bin/bash
export SRC_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export ROOT_DIR=${SRC_DIR%/*}
cd $ROOT_DIR

. ./starter.sh env

get_id_from_tfstate "AGENT_DATASOURCE_OCID" "starter_agent_ds" 
get_id_from_tfstate "AGENT_OCID" "starter_agent" 

# Upload Sample Files
sleep 5
oci os object bulk-upload -ns $TF_VAR_namespace -bn ${TF_VAR_prefix}-agent-bucket --src-dir ../sample_files --overwrite --content-type auto

# RAG - Ingestion
oci generative-ai-agent data-ingestion-job create --compartment-id $TF_VAR_compartment_ocid --data-source-id $AGENT_DATASOURCE_OCID

# Create tools
oci generative-ai-agent tool create-tool-rag-tool-config --agent-id $AGENT_OCID --compartment-id $TF_VAR_compartment_ocid --description rag-tool --tool-config-knowledge-base-configs xxx
oci generative-ai-agent tool create-tool-function-calling-tool-config --agent-id $AGENT_OCID --compartment-id $TF_VAR_compartment_ocid --description custom-tool --tool-config-function xxx
oci generative-ai-agent tool create-tool-sql-tool-config --agent-id $AGENT_OCID --compartment-id $TF_VAR_compartment_ocid --description sql-tool --tool-config-database-schema xxx --tool-conf
ig-dialect oracle       

title "INSTALLATION DONE"
echo
echo "-----------------------------------------------------------------------"
echo "Streamlit:"
echo "http://${BASTION_IP}:8080/"
echo

