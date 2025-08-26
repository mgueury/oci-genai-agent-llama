#!/usr/bin/env bash
export SRC_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export ROOT_DIR=${SRC_DIR%/*}
cd $ROOT_DIR

. ./starter.sh env

get_id_from_tfstate "AGENT_OCID" "starter_agent" 

# TOOLS DESTROY
oci generative-ai-agent tool list --agent-id $AGENT_OCID --compartment-id $TF_VAR_compartment_ocid --all > $TARGET_DIR/tools.json
for TOOL_OCID in `cat $TARGET_DIR/tools.json| jq -r '.data.items[] | .id'`;
do
   echo "Deleting agent tool: $TOOL_OCID"
   oci generative-ai-agent tool delete --tool-id $TOOL_OCID --force --wait-for-state SUCCEEDED --wait-for-state FAILED
done;
