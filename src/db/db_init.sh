#!/bin/bash
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
sqlplus -L $DB_USER/$DB_PASSWORD@DB @oracle.sql $DB_PASSWORD
sqlplus -L $DB_USER/$DB_PASSWORD@DB @dept_emp.sql $DB_PASSWORD

/usr/lib/oracle/21/client64/bin/sqlldr $DB_USER/$DB_PASSWORD@DB CONTROL=supportagents.ctl
/usr/lib/oracle/21/client64/bin/sqlldr $DB_USER/$DB_PASSWORD@DB CONTROL=tickets.ctl
