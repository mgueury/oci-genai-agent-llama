#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR
export PATH=~/.local/bin/:$PATH

. ./env.sh
source myenv/bin/activate
# python3 api_server.py 2>&1 | tee api_server.log
uvicorn api_server:app --host 0.0.0.0 --reload 2>&1 | tee api_server.log