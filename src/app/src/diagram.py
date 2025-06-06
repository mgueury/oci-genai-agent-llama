import streamlit as st
import oci
import json
import datetime
from oci import generative_ai_agent_runtime as genai_runtime

import os, io, glob
# from oci_models import get_llm
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain_community.chat_models.oci_generative_ai import ChatOCIGenAI

# --- Configuration ---
compartment_id = os.getenv("TF_VAR_compartment_ocid")
region = os.getenv("TF_VAR_region")
agent_endpoint = "https://agent-runtime.generativeai."+region+".oci.oraclecloud.com"
agent_id = os.getenv("TF_VAR_agent_endpoint_ocid")
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
config = {'region': signer.region, 'tenancy': signer.tenancy_id}

# --- Initialize client ---
client = genai_runtime.GenerativeAiAgentRuntimeClient(
    config = {}, 
    signer=signer,
    service_endpoint=agent_endpoint,
    retry_strategy=oci.retry.NoneRetryStrategy()
)

# --- Session Management ---
if "session_id" not in st.session_state:
    session_details = genai_runtime.models.CreateSessionDetails(
        display_name="Streamlit Chat Session",
        description="Chat UI with OCI Generative Agent"
    )
    session = client.create_session(session_details, agent_id)
    st.session_state.session_id = session.data.id

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Tool function ---
def email(customerEmail, subject, emailBodyContent):
    return {
        "confirmation": f"Email sent to {customerEmail} with subject '{subject}' and body '{emailBodyContent[:30]}...'"
    }

def generate_architecture_diagram(steps: str):
    template = """
    You are an expert cloud engineer who writes clean, syntactically correct Python code using the diagrams module.

    Your task:
    - ONLY use Oracle Cloud Infrastructure (OCI) classes from the diagrams.oci.* modules listed below.
    - DO NOT invent or guess class names that are not in this list.

    Valid Classes (examples from each module):
    - diagrams.oci.compute: VM, Container, OKE, BareMetal, Functions, InstancePools, OCIR, Autoscale
    - diagrams.oci.network: Vcn, LoadBalancer, InternetGateway, ServiceGateway, RouteTable, Firewall, Drg
    - diagrams.oci.connectivity: FastConnect, NATGateway, VPN, DNS, CustomerPremises
    - diagrams.oci.database: Autonomous, BigdataService, DatabaseService, Stream, DMS, DataflowApache
    - diagrams.oci.devops: APIGateway, APIService, ResourceMgmt
    - diagrams.oci.monitoring: Alarm, Events, Workflow, Notifications, Queue
    - diagrams.oci.security: WAF, Vault, CloudGuard, KeyManagement, DDOS, Encryption
    - diagrams.oci.storage: ObjectStorage, FileStorage, Buckets, StorageGateway, BackupRestore
    - Make sure each class is imported from the correct module as shown.

    Instructions:
    - Start with: `from diagrams import Diagram, Cluster`
    - Only include valid Python code (no explanations or markdown).
    - Use `show=False` in the Diagram constructor.
    - Create a file named "diagram.png"

    Now, generate the code based only on the following request:

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
    # llm = get_llm(temperature=0.0)
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
    if files:
        return {"diagram_path": files[0]}
    return {"diagram_path": None}

# --- Required Actions Handler ---
def handle_required_actions(response_data):
    performed_actions = []
    for action in response_data.required_actions or []:
        if action.required_action_type == "FUNCTION_CALLING_REQUIRED_ACTION":
            fn = action.function_call
            args = json.loads(fn.arguments)
            if fn.name == "email":
                result = email(**args)
            elif fn.name == "generate_architecture_diagram":
                result = generate_architecture_diagram(**args)
            else:
                result = { "unknown tool", fn.name }
            performed_actions.append({
                "actionId": action.action_id,
                "performedActionType": "FUNCTION_CALLING_PERFORMED_ACTION",
                "functionCallOutput": json.dumps(result)
            })
    return performed_actions

# --- UI ---
st.title("OCI Generative Agent Chat")
st.caption("Interact with your agent using function-calling tools, RAG, SQL, and now diagrams!")

# --- Input form ---
with st.form("chat_form"):
    user_input = st.text_input("What would you like to ask the agent?")
    submit = st.form_submit_button("Send")

# --- Main Interaction ---
if submit and user_input.strip():
    with st.spinner("Asking the agent..."):
        chat_details = genai_runtime.models.ChatDetails(
            user_message=user_input,
            should_stream=False,
            session_id=st.session_state.session_id
        )
        response = client.chat(agent_id, chat_details)

        # Handle any required actions
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

        # --- Robust diagram path extraction ---
        import re
        try:
            # Case 1: JSON-style result
            parsed = json.loads(raw_reply)
            if isinstance(parsed, dict) and "diagram_path" in parsed:
                diagram_path = parsed["diagram_path"]
        except Exception:
            pass

        # Case 2: plain text with .png path
        if not diagram_path and ".png" in raw_reply:
            match = re.search(r'(/.*?\.png)', raw_reply)
            if match:
                potential_path = match.group(1)
                if os.path.exists(potential_path):
                    diagram_path = potential_path

        # Display image if found
        if diagram_path:
            st.image(diagram_path, caption="Generated Architecture Diagram")
            final_reply = "Here is the architecture diagram based on your request."

        # Format SQL outputs nicely
        try:
            if "executionResult" in raw_reply:
                parsed = json.loads(raw_reply)
                if "executionResult" in parsed:
                    results = parsed["executionResult"]
                    if results and isinstance(results, list):
                        final_reply = ", ".join(f"{k}: {v}" for k, v in results[0].items())
        except Exception:
            pass

        # Add to chat history
        st.session_state.chat_history.append(("You", user_input))
        st.session_state.chat_history.append(("Agent", {
            "text": final_reply,
            "image": diagram_path
        } if diagram_path else final_reply))

# --- Display history ---
st.markdown("## Chat History")
for speaker, msg in st.session_state.chat_history[::-1]:
    st.markdown(f"**{speaker}:**")
    if isinstance(msg, dict):
        st.markdown(msg["text"])
        if msg.get("image"):
            st.image(msg["image"])
    else:
        st.markdown(msg)