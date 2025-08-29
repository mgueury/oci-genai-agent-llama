#!/usr/bin/env bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

# Install SQL*Plus
if [[ `arch` == "aarch64" ]]; then
  sudo dnf install -y oracle-release-el8 
  sudo dnf install -y oracle-instantclient19.19-basic oracle-instantclient19.19-sqlplus oracle-instantclient19.19-tools
else
  sudo dnf install -y oracle-instantclient-release-el8
  sudo dnf install -y oracle-instantclient-basic oracle-instantclient-sqlplus oracle-instantclient-tools
fi

# Install the tables
cat > tnsnames.ora <<EOT
DB  = $DB_URL
EOT

export TNS_ADMIN=$SCRIPT_DIR
export NLS_LANG=AMERICAN_AMERICA.UTF8

# Install SQLCL (Java program)
wget https://download.oracle.com/otn_software/java/sqldeveloper/sqlcl-latest.zip
rm -Rf sqlcl
unzip sqlcl-latest.zip
sudo dnf install -y java-17 

# Create the script to install the APEX Application
cat > import_application.sql << EOF 
create user if not exists apex_app identified by "$DB_PASSWORD" default tablespace USERS quota unlimited on USERS temporary tablespace TEMP; 
/
grant connect, resource, unlimited tablespace to apex_app;
/
EXEC DBMS_CLOUD_ADMIN.ENABLE_RESOURCE_PRINCIPAL('APEX_APP');
grant execute on DBMS_CLOUD to APEX_APP;
grant execute on DBMS_CLOUD_AI to APEX_APP;
grant execute on DBMS_SCHEDULER to APEX_APP;
grant create any job to APEX_APP;
/
begin
    apex_instance_admin.add_workspace(
     p_workspace_id   => null,
     p_workspace      => 'APEX_APP',
     p_primary_schema => 'APEX_APP');
end;
/
begin
    apex_application_install.set_workspace('APEX_APP');
    apex_application_install.set_application_id(1001);
    apex_application_install.generate_offset();
    apex_application_install.set_schema('APEX_APP');
    apex_application_install.set_application_alias('APEX_APP');
    apex_application_install.set_auto_install_sup_obj( true );
end;
/
declare
    l_workspace_id number;
    l_group_id     number;
begin
    apex_application_install.set_workspace('APEX_APP');
    l_workspace_id := apex_util.find_security_group_id('APEX_APP');
    apex_util.set_security_group_id(l_workspace_id);
    -- l_group_id := apex_util.get_group_id('APEX_APP');
    apex_util.create_user(p_user_name           => 'APEX_APP',
                        p_email_address         => 'spam@oracle.com',
                        p_web_password          => '$DB_PASSWORD',
                        p_default_schema        => 'APEX_APP',
                        p_change_password_on_first_use => 'N',
                        p_developer_privs       => 'ADMIN:CREATE:DATA_LOADER:EDIT:HELP:MONITOR:SQL',
                        p_allow_app_building_yn => 'Y',
                        p_allow_sql_workshop_yn => 'Y',
                        p_allow_websheet_dev_yn => 'Y',
                        p_allow_team_development_yn => 'Y');                          
    COMMIT;                      
end;
/
@apex_app.sql

grant all on tickets to APEX_APP;

BEGIN
  update tickets set description=replace(description, '\n', chr(13) );
  COMMIT;
END;
/

BEGIN
  ORDS.enable_schema(
    p_enabled             => TRUE,
    p_schema              => 'APEX_APP',
    p_url_mapping_type    => 'BASE_PATH',
    p_url_mapping_pattern => 'apex_app',
    p_auto_rest_auth      => FALSE
  );  
  COMMIT;
END;
/

connect APEX_APP/&1@DB

BEGIN
  ORDS.define_module(
    p_module_name    => 'module',
    p_base_path      => 'module/',
    p_items_per_page => 0);

  ORDS.define_template(
   p_module_name    => 'module',
   p_pattern        => 'insert');

  -- XXX pn_status needed ??
  ORDS.define_handler(
    p_module_name    => 'module',
    p_pattern        => 'insert',
    p_method         => 'GET',
    p_source_type    => ords.source_type_plsql,
    p_source         => 'DECLARE 
  TID number;
BEGIN
  :pn_status := 200;
  if :title is not null then
      HTP.print(''created SR '' || :title);  
      select max(t.ticketid)+1 into tid from ADMIN.TICKETS t;
      INSERT INTO ADMIN.TICKETS (
        TICKETID,
        CUSTOMERNAME,
        SUBJECT,
        DESCRIPTION,
        CREATEDDATE,
        LASTUPDATEDDATE,
        STATUSID,
        ASSIGNEDTOAGENTID
      ) VALUES ( TID,
        ''CustomerODRS'',
        :title,
        nvl(:question, ''-''),
        SYSDATE,
        SYSDATE,
        1,
        2 );    
   else
     HTP.print(''<br>no title'');
   end if;
END;');
  commit;                      
end;                        
/

EXIT
-- GET http://ords_url/ords/apex_app/module/dept
-- GET http://ords_url/ords/apex_app/module/info


quit
EOF

sqlplus -L $DB_USER/$DB_PASSWORD@DB @tables.sql $DB_PASSWORD
sqlcl/bin/sql $DB_USER/$DB_PASSWORD@DB @import_application.sql

/usr/lib/oracle/21/client64/bin/sqlldr $DB_USER/$DB_PASSWORD@DB CONTROL=supportagents.ctl
/usr/lib/oracle/21/client64/bin/sqlldr $DB_USER/$DB_PASSWORD@DB CONTROL=tickets.ctl
/usr/lib/oracle/21/client64/bin/sqlldr APEX_APP/$DB_PASSWORD@DB CONTROL=ai_eval_question_answer.ctl
