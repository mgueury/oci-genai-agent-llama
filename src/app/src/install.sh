#!/usr/bin/env bash
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


# Configure APEX settings
. ./env.sh
export TNS_ADMIN=$HOME/db
$HOME/db/sqlcl/bin/sql $DB_USER/$DB_PASSWORD@DB << EOF
begin
  update APEX_APP.AI_CONFIG set value='$TF_VAR_compartment_ocid' where key='compartment_ocid';
  update APEX_APP.AI_CONFIG set value='https://$APIGW_HOSTNAME/app/chat' where key='qa_url';
  update APEX_APP.AI_CONFIG set value='$TF_VAR_region' where key='region';
  update APEX_APP.AI_CONFIG set value='$TF_VAR_genai_meta_model' where key='llama_model';
  commit;
end;
/
exit;
EOF

# Configure for React
sudo dnf module enable -y nodejs:18
sudo dnf module install -y nodejs

cd react
npm install
npm run build

# Firewall
# - FastAPI
sudo firewall-cmd --zone=public --add-port=8000/tcp --permanent
# - React
sudo firewall-cmd --zone=public --add-port=3000/tcp --permanent
sudo firewall-cmd --reload

# Nginx - comment the "location /"
sudo dnf install nginx -y > /tmp/dnf_nginx.log
sudo ls /etc/nginx
sudo sed -i '/^ *location \/ {/,/^ *}/s/^/# /' /etc/nginx/nginx.conf
