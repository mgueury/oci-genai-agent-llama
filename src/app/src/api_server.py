# === api_server.py ===

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
from oci import generative_ai_agent_runtime as genai_runtime
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
import os, glob
import oci


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

# --- Utils ---
def ensure_session(existing_session_id=None):
    if existing_session_id:
        try:
            client.get_session(agent_id, existing_session_id)
            return existing_session_id
        except:
            pass
    session_details = genai_runtime.models.CreateSessionDetails(
        display_name="Auto Session", description="New session"
    )
    session = client.create_session(session_details, agent_id)
    return session.data.id

def generate_architecture_diagram(steps: str):
    prompt = ChatPromptTemplate.from_template("""
    You are an expert OCI engineer. Output clean Python code using the diagrams module only.
    Steps: {steps}
    Code:
    """)
    llm = ChatOCIGenAI(
        auth_type='INSTANCE_PRINCIPAL',
        model_id=os.getenv("TF_VAR_genai_meta_model"),
        service_endpoint="https://inference.generativeai."+region+".oci.oraclecloud.com",
        model_kwargs={"temperature": 0.0, "max_tokens": 4000},
        compartment_id=compartment_id
    ) 
    chain = LLMChain(llm=llm, prompt=prompt)
    code = chain.invoke({"steps": steps})["text"].replace("`", "").replace("python", "")

    for f in glob.glob("*.png"):
        os.remove(f)
    with open("codesample.py", "w") as f:
        f.write(code)
    os.system("python codesample.py")
    files = glob.glob("*.png")
    return {"diagram_path": files[0]} if files else {"diagram_path": None}

def handle_required_actions(response_data):
    results = []
    for action in response_data.required_actions or []:
        if action.required_action_type == "FUNCTION_CALLING_REQUIRED_ACTION":
            fn = action.function_call
            args = json.loads(fn.arguments)
            output = {}
            if fn.name == "email":
                output = {"confirmation": f"Email sent to {args['customerEmail']}"}
            elif fn.name == "generate_architecture_diagram":
                output = generate_architecture_diagram(**args)
            results.append({
                "actionId": action.action_id,
                "performedActionType": "FUNCTION_CALLING_PERFORMED_ACTION",
                "functionCallOutput": json.dumps(output)
            })
    return results

# --- FastAPI setup ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/session")
def create_session():
    return {"session_id": ensure_session()}

@app.get("/evaluate")
def evaluate(
    question: str = Query(..., description="Ask a question like 'show ticket 1052'"),
    session_id: str = Query(None, description="Optional session ID")
):
    sid = ensure_session(session_id)
    chat_details = genai_runtime.models.ChatDetails(user_message=question, should_stream=False, session_id=sid)
    response = client.chat(agent_id, chat_details)

    actions = handle_required_actions(response.data)
    if actions:
        chat_details = genai_runtime.models.ChatDetails(
            user_message="", should_stream=False, session_id=sid, performed_actions=actions
        )
        response = client.chat(agent_id, chat_details)

    try:
        parsed_answer = json.loads(response.data.message.content.text)
    except:
        parsed_answer = {"text": response.data.message.content.text}

    return {
        "question": question,
        "answer": parsed_answer,
        "session_id": sid
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)