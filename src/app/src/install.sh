#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

# https://yum.oracle.com/oracle-linux-python.html

sudo dnf install -y graphviz
sudo dnf install -y python3.12 python3.12-pip python3-devel
sudo pip3.12 install pip --upgrade

# Install virtual env python_env
python3.12 -m venv myenv
source myenv/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt

# FastAPI
sudo firewall-cmd --zone=public --add-port=8000/tcp --permanent
sudo firewall-cmd --reload

# Configure APEX settings
export TNS_ADMIN=$HOME/db
$HOME/db/sqlcl/bin/sql $DB_USER/$DB_PASSWORD@DB << EOF
begin
  update APEX_APP.AI_CONFIG set value='$TF_VAR_compartment_ocid' where key='compartment_ocid';
  update APEX_APP.AI_CONFIG set value='https://$APIGW_HOSTNAME/app/evaluate?question=' where key='qa_url';
  update APEX_APP.AI_CONFIG set value='$TF_VAR_region' where key='region';
  update APEX_APP.AI_CONFIG set value='$TF_VAR_genai_meta_model' where key='llama_model';
  commit;
end;
/
exit;
EOF