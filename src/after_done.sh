#!/bin/bash
export SRC_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export ROOT_DIR=${SRC_DIR%/*}
cd $ROOT_DIR

. ./starter.sh env

get_id_from_tfstate "AGENT_DATASOURCE_OCID" "starter_agent_ds" 
get_id_from_tfstate "AGENT_OCID" "starter_agent" 
get_id_from_tfstate "AGENT_KB_OCID" "starter_agent_kb" 
get_id_from_tfstate "DBTOOLS_OCID" "starter_dbtools_connection" 

# Upload Sample Files
sleep 5
oci os object bulk-upload -ns $TF_VAR_namespace -bn ${TF_VAR_prefix}-agent-bucket --src-dir sample_files --overwrite --content-type auto

# RAG - Ingestion
oci generative-ai-agent data-ingestion-job create --compartment-id $TF_VAR_compartment_ocid --data-source-id $AGENT_DATASOURCE_OCID

# AGENT TOOLS
## RAG-TOOL
oci generative-ai-agent tool create-tool-rag-tool-config \
  --agent-id $AGENT_OCID \
  --compartment-id $TF_VAR_compartment_ocid \
  --display-name rag-tool \
  --description rag-tool \
  --tool-config-knowledge-base-configs "[{
    \"knowledgeBaseId\": \"${AGENT_KB_OCID}\"
  }]"

## FUNCTION-TOOL
oci generative-ai-agent tool create-tool-function-calling-tool-config \
  --agent-id $AGENT_OCID \
  --compartment-id $TF_VAR_compartment_ocid \
  --display-name custom-tool \
  --description custom-tool \
  --tool-config-function "{
    \"name\": \"add\",
    \"description\": \"Add 2 numbers\",
    \"parameters\": {
        \"type\": \"object\",
        \"properties\": \"{\\\"number1\\\":{\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"Number 1 to add \\\"},\\\"number2\\\":{\\\"type\\\":\\\"string\\\",\\\"description\\\":\\\"Number 2 to add\\\"}}\",
        \"required\": \"[\\\"number1\\\",\\\"number2\\\"]\",
        \"additionalProperties\": \"false\"
    }
  }"

## SQL-TOOL
oci generative-ai-agent tool create-tool-sql-tool-config \
  --agent-id $AGENT_OCID \
  --compartment-id $TF_VAR_compartment_ocid \
  --display-name sql-tool \
  --description sql-tool \
  --tool-config-database-connection "{
    \"connectionId\": \"${DBTOOLS_OCID}\",
    \"connectionType\": \"DATABASE_TOOL_CONNECTION\"
  }" \
  --tool-config-database-schema "{
    \"inputLocationType\": \"INLINE\",
    \"content\": \"create table dept(  \\ndeptno     number(2,0),  \\ndname      varchar2(14),  \\nloc        varchar2(13),  \\nconstraint pk_dept primary key (deptno)  \\n);\\n\\ncreate table emp(  \\nempno    number(4,0),  \\nename    varchar2(10),  \\njob      varchar2(9),  \\nmgr      number(4,0),  \\nhiredate date,  \\nsal      number(7,2),  \\ncomm     number(7,2),  \\ndeptno   number(2,0),  \\nconstraint pk_emp primary key (empno),  \\nconstraint fk_deptno foreign key (deptno) references dept (deptno)  \\n);\"     
  }" \
  --tool-config-table-and-column-description "{
    \"inputLocationType\": \"INLINE\",
    \"content\": \"Description of the important tables in the schema:\n\nEMP         Employee names and other information\nDEPT        Department names and other information \n\nDescription of the important columns of the tables in the schema:\n\nEMP TABLE    \nemp.empno: Employee number (a unique identifier for each employee).\nemp.ename: Employee name (the name of the employee in uppercase).\nemp.job: Employee job title (the employee's job in uppercase, e.g., 'MANAGER', 'CLERK').\nemp.mgr: Manager employee number (the empno of the employee's manager).  This establishes a hierarchical relationship within the employees.\nemp.hiredate: Employee hire date (the date when the employee was hired).\nemp.sal: Employee salary (the employee's salary).\nemp.comm: Employee commission (any commission earned by the employee).\nemp.deptno: Department number (the deptno of the department the employee belongs to).  This is a foreign key linking back to the dept table.\n\nDEPT TABLE    \ndept.deptno: Department number (a unique identifier for each department).\ndept.dname: Department name (the name of the department in uppercase, e.g., 'SALES', 'ACCOUNTING').\ndept.loc: Location of the department (the city in uppercase where the department is located).\"
  }" \
  --tool-config-should-enable-self-correction true \
  --tool-config-dialect ORACLE_SQL \
  --tool-config-model-size LARGE

title "INSTALLATION DONE"
echo
echo "-----------------------------------------------------------------------"
echo "Streamlit:"
echo "http://${BASTION_IP}:8080/"
echo

