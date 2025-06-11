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
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI

# Test API
# curl http://localhost:8000/evaluate?question=Who%20is%20the%20busiest%20agent%3F
# curl https://apigw/app/evaluate?question=Who%20is%20the%20busiest%20agent%3F

# --- Configuration ---
compartment_id = os.getenv("TF_VAR_compartment_ocid")
region = os.getenv("TF_VAR_region")
agent_endpoint = "https://agent-runtime.generativeai."+region+".oci.oraclecloud.com"
agent_id = os.getenv("TF_VAR_agent_endpoint_ocid")
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}

client = genai_runtime.GenerativeAiAgentRuntimeClient(
    config = {}, 
    signer=signer,
    service_endpoint=agent_endpoint,
    retry_strategy=oci.retry.NoneRetryStrategy()
)

# --- Session Management ---
session_id = None
def ensure_session():
    global session_id
    if session_id is None:
        session_details = genai_runtime.models.CreateSessionDetails(
            display_name="Unified Session",
            description="Shared session for Streamlit and FastAPI"
        )
        session = client.create_session(session_details, agent_id)
        session_id = session.data.id
    return session_id

# --- Tool function (email, diagram) ---
def email(customerEmail, subject, emailBodyContent):
    return {
        "confirmation": f"Email sent to {customerEmail} with subject '{subject}' and body '{emailBodyContent[:30]}...'"
    }

def generate_architecture_diagram(steps: str):
    template = """
    You are an expert cloud engineer who writes clean, syntactically correct Python code using the diagrams module.
    ONLY use valid OCI classes listed below.
    Start your code with 'from diagrams import Diagram, Cluster' and use show=False.
    Create a file named "diagram.png"    

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
    llm = ChatOCIGenAI(
        auth_type='INSTANCE_PRINCIPAL',
        model_id=os.getenv("TF_VAR_genai_meta_model"),
        service_endpoint="https://inference.generativeai."+region+".oci.oraclecloud.com",
        model_kwargs={"temperature": 0.0, "max_tokens": 4000},
        compartment_id=compartment_id
    ) 
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

# --- Required Action Handler ---
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

# === Streamlit Chat UI ===
st.set_page_config(page_title="GenAI Chat")
st.title("OCI Generative Agent Chat")
st.caption("Ask questions, trigger tools, or generate OCI diagrams.")

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

        performed_actions = handle_required_actions(response.data)
        if performed_actions:
            chat_details = genai_runtime.models.ChatDetails(
                user_message="",
                should_stream=False,
                session_id=st.session_state.session_id,
                performed_actions=performed_actions
            )
            response = client.chat(agent_id, chat_details)

        raw_reply = response.data.message.content.text
        final_reply = raw_reply
        diagram_path = None

        try:
            parsed = json.loads(raw_reply)
            if isinstance(parsed, dict) and "diagram_path" in parsed:
                diagram_path = parsed["diagram_path"]
        except Exception:
            pass

        if not diagram_path and ".png" in raw_reply:
            match = re.search(r'(/.*?\.png)', raw_reply)
            if match and os.path.exists(match.group(1)):
                diagram_path = match.group(1)

        if diagram_path:
            st.image(diagram_path, caption="Generated Architecture Diagram")
            final_reply = "Here is the architecture diagram based on your request."

        try:
            if "executionResult" in raw_reply:
                parsed = json.loads(raw_reply)
                if "executionResult" in parsed:
                    results = parsed["executionResult"]
                    if results and isinstance(results, list):
                        final_reply = ", ".join(f"{k}: {v}" for k, v in results[0].items())
        except Exception:
            pass

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

# === FastAPI REST endpoint ===
api = FastAPI()
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@api.get("/evaluate")
def evaluate(question: str = Query(..., description="Ask a question to the agent")):
    # session_id = ensure_session()
    session_details = genai_runtime.models.CreateSessionDetails(
        display_name="Unified Session",
        description="Shared session for Streamlit and FastAPI"
    )
    session = client.create_session(session_details, agent_id)
    session_id = session.data.id

    chat_details = genai_runtime.models.ChatDetails(
        user_message=question,
        should_stream=False,
        session_id=session_id
    )
    response = client.chat(agent_id, chat_details)

    performed = handle_required_actions(response.data)
    if performed:
        chat_details = genai_runtime.models.ChatDetails(
            user_message="",
            should_stream=False,
            session_id=session_id,
            performed_actions=performed
        )
        response = client.chat(agent_id, chat_details)

    answer = response.data.message.content.text
    return {"question": question, "answer": answer}

# === Start FastAPI in background with Streamlit ===
def run_api():
    uvicorn.run(api, host="0.0.0.0", port=8000)

print( "hello", flush=True )
threading.Thread(target=run_api, daemon=True).start()