import streamlit as st
import oci
import json
import os
import re
import glob
import threading
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from oci import generative_ai_agent_runtime as genai_runtime
from oci_models import get_llm
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

# --- OCI Configuration ---
agent_endpoint = "https://agent-runtime.generativeai.eu-frankfurt-1.oci.oraclecloud.com"
agent_id = "ocid1.genaiagentendpoint.oc1.eu-frankfurt-1.amaaaaaa2xxap7yaluauwhdt73qzvkqd2fdjstr6wa5a32f7qijeci5f4fbq"
config = oci.config.from_file("~/.oci/config", "DEFAULT")

client = genai_runtime.GenerativeAiAgentRuntimeClient(
    config=config,
    service_endpoint=agent_endpoint,
    retry_strategy=oci.retry.NoneRetryStrategy()
)

# --- Create or validate session ---
def ensure_session(existing_session_id=None):
    if existing_session_id:
        try:
            # Dummy ping to validate session
            client.get_session(agent_id, existing_session_id)
            return existing_session_id
        except Exception:
            pass
    session_details = genai_runtime.models.CreateSessionDetails(
        display_name="Generated Session",
        description="Auto-created session"
    )
    session = client.create_session(session_details, agent_id)
    return session.data.id

# --- Tool functions ---
def email(customerEmail, subject, emailBodyContent):
    return {
        "confirmation": f"Email sent to {customerEmail} with subject '{subject}' and body '{emailBodyContent[:30]}...'"
    }

def generate_architecture_diagram(steps: str):
    template = """
    You are an expert cloud engineer who writes clean, syntactically correct Python code using the diagrams module.
    ONLY use valid OCI classes listed below.
    Start your code with 'from diagrams import Diagram, Cluster' and use show=False.

    Valid Classes:
    - diagrams.oci.compute: VM, Container, OKE, BareMetal, Functions, InstancePools, OCIR, Autoscale
    - diagrams.oci.network: Vcn, LoadBalancer, InternetGateway, ServiceGateway, RouteTable, Firewall, Drg
    - diagrams.oci.connectivity: FastConnect, NATGateway, VPN, DNS, CustomerPremises
    - diagrams.oci.database: Autonomous, BigdataService, DatabaseService, Stream, DMS, DataflowApache
    - diagrams.oci.devops: APIGateway, APIService, ResourceMgmt
    - diagrams.oci.monitoring: Alarm, Events, Workflow, Notifications, Queue
    - diagrams.oci.security: WAF, Vault, CloudGuard, KeyManagement, DDOS, Encryption
    - diagrams.oci.storage: ObjectStorage, FileStorage, Buckets, StorageGateway, BackupRestore

    Steps:
    {steps}

    Code:
    """
    prompt = ChatPromptTemplate.from_template(template)
    llm = get_llm(temperature=0.0)
    qa_chain = LLMChain(llm=llm, prompt=prompt)
    response = qa_chain.invoke({"steps": steps})
    code = response["text"].replace("`", "").replace("python", "")

    cwd = os.getcwd()
    for file in glob.glob(cwd + "/*.png"):
        os.remove(file)

    with open("codesample.py", "w", encoding="utf-8") as f:
        f.write(code)

    os.system("python codesample.py")
    files = glob.glob(cwd + "/*.png")
    return {"diagram_path": files[0]} if files else {"diagram_path": None}

# --- Handle required actions ---
def handle_required_actions(response_data):
    performed_actions = []
    for action in response_data.required_actions or []:
        if action.required_action_type == "FUNCTION_CALLING_REQUIRED_ACTION":
            fn = action.function_call
            args = json.loads(fn.arguments)
            result = {}
            if fn.name == "email":
                result = email(**args)
            elif fn.name == "generate_architecture_diagram":
                result = generate_architecture_diagram(**args)
            performed_actions.append({
                "actionId": action.action_id,
                "performedActionType": "FUNCTION_CALLING_PERFORMED_ACTION",
                "functionCallOutput": json.dumps(result)
            })
    return performed_actions

# === Streamlit ===
st.set_page_config(page_title="GenAI Chat")
st.title("OCI Generative Agent Chat")
st.caption("Ask anything like: 'Show ticket 1052' or generate diagrams.")

if "session_id" not in st.session_state:
    st.session_state.session_id = ensure_session()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.form("chat_form"):
    user_input = st.text_input("Ask the agent something...")
    submit = st.form_submit_button("Send")

if submit and user_input.strip():
    with st.spinner("Thinking..."):
        chat_details = genai_runtime.models.ChatDetails(
            user_message=user_input,
            should_stream=False,
            session_id=st.session_state.session_id
        )
        response = client.chat(agent_id, chat_details)

        actions = handle_required_actions(response.data)
        if actions:
            chat_details = genai_runtime.models.ChatDetails(
                user_message="",
                should_stream=False,
                session_id=st.session_state.session_id,
                performed_actions=actions
            )
            response = client.chat(agent_id, chat_details)

        raw_reply = response.data.message.content.text
        final_reply = raw_reply
        diagram_path = None

        try:
            parsed = json.loads(raw_reply)
            if isinstance(parsed, dict) and "executionResult" in parsed:
                query = parsed.get("generatedQuery", "")
                results = parsed["executionResult"]
                if results and isinstance(results, list):
                    import pandas as pd
                    df = pd.DataFrame(results)
                    st.write("**Generated Query:**")
                    st.code(query, language="sql")
                    st.write("**Execution Result:**")
                    st.dataframe(df)
                    final_reply = ""
        except Exception as e:
            print("Failed to parse agent response:", e)

        if not diagram_path and ".png" in raw_reply:
            match = re.search(r'(/.*?\.png)', raw_reply)
            if match and os.path.exists(match.group(1)):
                diagram_path = match.group(1)

        if diagram_path:
            st.image(diagram_path, caption="Generated Architecture Diagram")
            final_reply = "Here is the architecture diagram."

        st.session_state.chat_history.append(("You", user_input))
        st.session_state.chat_history.append(("Agent", {
            "text": final_reply,
            "image": diagram_path
        } if diagram_path else final_reply))

st.markdown("## Chat History")
for speaker, msg in st.session_state.chat_history[::-1]:
    st.markdown(f"**{speaker}:**")
    if isinstance(msg, dict):
        st.markdown(msg["text"])
        if msg.get("image"):
            st.image(msg["image"])
    else:
        st.markdown(msg)

# === FastAPI ===
api = FastAPI()
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@api.get("/evaluate")
def evaluate(
    question: str = Query(..., description="Ask a question like 'show ticket 1052'"),
    session_id: str = Query(None, description="Optional session ID")
):
    sid = ensure_session(session_id)
    chat_details = genai_runtime.models.ChatDetails(
        user_message=question,
        should_stream=False,
        session_id=sid
    )
    response = client.chat(agent_id, chat_details)

    actions = handle_required_actions(response.data)
    if actions:
        chat_details = genai_runtime.models.ChatDetails(
            user_message="",
            should_stream=False,
            session_id=sid,
            performed_actions=actions
        )
        response = client.chat(agent_id, chat_details)

    answer = response.data.message.content.text
    return {"question": question, "answer": answer, "session_id": sid}

@api.get("/session")
def create_new_session():
    new_sid = ensure_session()
    return {"session_id": new_sid}

# === Start FastAPI in background ===
def run_api():
    uvicorn.run(api, host="0.0.0.0", port=8000)

if os.environ.get("RUN_MAIN") != "true": 
    threading.Thread(target=run_api, daemon=True).start()