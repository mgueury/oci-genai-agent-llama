from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import FileResponse
import json, os, glob, base64
import oci
from oci import generative_ai_agent_runtime as genai_runtime
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain_community.chat_models import ChatOCIGenAI

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

def get_llm(temperature=0, max_tokens=4000):
    """
    Initialize and return an instance of ChatOCIGenAI with the specified configuration.

    Returns:
        ChatOCIGenAI: An instance of the OCI GenAI language model.
    """
    llm = ChatOCIGenAI(
        auth_type='INSTANCE_PRINCIPAL',
        model_id=os.getenv("TF_VAR_genai_meta_model"),
        service_endpoint="https://inference.generativeai."+region+".oci.oraclecloud.com",
        model_kwargs={"temperature": temperature, "max_tokens": max_tokens},
        compartment_id=compartment_id
    )     
    return llm

# --- FastAPI App ---
app = FastAPI()

# --- Request Model ---
class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    execute_functions: Optional[bool] = True

# --- Session Management ---
def ensure_session(session_id=None):
    if session_id:
        try:
            client.get_session(agent_id, session_id)
            return session_id
        except:
            pass
    session_details = genai_runtime.models.CreateSessionDetails(
        display_name="API Chat Session",
        description="Session from React UI"
    )
    session = client.create_session(session_details, agent_id)
    return session.data.id

# --- Base64 Helper ---
def encode_image_to_base64(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# --- Diagram Generation ---
def generate_architecture_diagram(**kwargs):
    steps = kwargs.get("steps") or kwargs.get("message")
    if not steps:
        raise ValueError("Missing 'steps' or 'message' input for diagram generation")

    prompt = ChatPromptTemplate.from_template("""
    You are an expert cloud engineer who writes clean, syntactically correct Python code using the diagrams module.

    Your task:
    - ONLY use Oracle Cloud Infrastructure (OCI) classes from the diagrams.oci.* modules listed below.
    - DO NOT invent or guess class names that are not in this list.
    - NEVER include explanations, comments, or markdown formatting. Just code.

    Valid Classes:
    - diagrams.oci.compute: VM, Functions
    - diagrams.oci.network: Vcn, LoadBalancer, InternetGateway
    - diagrams.oci.database: Autonomous
    - diagrams.oci.storage: ObjectStorage

    Start with: from diagrams import Diagram, Cluster
    Use show=False in the Diagram constructor.

    Now generate code for this:
    {steps}

    Code:
    """)

    llm = get_llm(temperature=0.0)
    chain = LLMChain(llm=llm, prompt=prompt)
    response = chain.invoke({"steps": steps})
    code = response["text"]

    code_lines = []
    for line in code.splitlines():
        if line.strip().startswith("```") or "does not exist" in line.lower():
            continue
        code_lines.append(line)
    code = "\n".join(code_lines)

    for f in glob.glob("*.png"):
        os.remove(f)

    with open("codesample.py", "w") as f:
        f.write(code)

    os.system("python3 codesample.py")

    files = glob.glob("*.png")
    if files:
        diagram_path = files[0]
        encoded = encode_image_to_base64(diagram_path)
        return {"diagram_base64": encoded}
    return {"diagram_base64": None}

# --- Handle Required Actions from Agent ---
def handle_required_actions(response_data, execute=True):
    if not execute:
        return []
    results = []
    for action in response_data.required_actions or []:
        if action.required_action_type == "FUNCTION_CALLING_REQUIRED_ACTION":
            fn = action.function_call
            args = json.loads(fn.arguments)
            if fn.name == "email":
                output = {"confirmation": f"Email sent to {args['customerEmail']}"}
            elif fn.name == "generate_architecture_diagram":
                output = generate_architecture_diagram(**args)
            else:
                output = {"error": "Unknown function"}
            results.append({
                "actionId": action.action_id,
                "performedActionType": "FUNCTION_CALLING_PERFORMED_ACTION",
                "functionCallOutput": json.dumps(output)
            })
    return results

# --- Process_citations ---
def process_citations(raw_citations):
    """Process raw citations into frontend-friendly format"""
    if not raw_citations:
        return []
    
    processed = []
    for citation in raw_citations:
        try:
            processed_citation = {
                "citation_id": getattr(citation, 'doc_id', ''),
                "content": getattr(citation, 'source_text', ''),
                "document_name": getattr(citation, 'title', 'Unknown Source'),
                "page_numbers": getattr(citation, 'page_numbers', []),
                "source_url": None,
                "storage_provider": None
            }
            
            if hasattr(citation, 'source_location') and citation.source_location:
                processed_citation["source_url"] = getattr(citation.source_location, 'url', None)
                processed_citation["storage_provider"] = getattr(citation.source_location, 'source_location_type', None)
            
            processed.append(processed_citation)
        except Exception as e:
            logger.error(f"Error processing citation: {e}")
            continue
    
    return processed

# --- Main Chat Endpoint ---
@app.post("/chat")
async def chat(request: ChatRequest):
    sid = ensure_session(request.session_id)

    chat_details = genai_runtime.models.ChatDetails(
        user_message=request.question,
        should_stream=False,
        session_id=sid
    )
    response = client.chat(agent_id, chat_details)

    actions = handle_required_actions(response.data, execute=request.execute_functions)
    diagram_base64 = None

    if actions:
        chat_details = genai_runtime.models.ChatDetails(
            user_message="",
            should_stream=False,
            session_id=sid,
            performed_actions=actions
        )
        response = client.chat(agent_id, chat_details)
        for action in actions:
            try:
                output = json.loads(action["functionCallOutput"])
                if "diagram_base64" in output:
                    diagram_base64 = output["diagram_base64"]
            except:
                pass

    msg_obj = response.data.message
    msg = msg_obj.content.text
    citations = process_citations(
        msg_obj.content.citations if hasattr(msg_obj.content, "citations") else None
    )


    answer = msg
    sql_result = None
    rag_context = None

    try:
        parsed = json.loads(msg)
        if isinstance(parsed, dict):
            answer = parsed.get("text", msg)
            sql_result = parsed.get("executionResult") or parsed.get("sql_result")
            rag_context = parsed.get("rag_context")
            if not diagram_base64:
                diagram_base64 = parsed.get("diagram_base64")
    except:
        pass

    return {
        "answer": answer,
        "session_id": sid,
        "diagram_base64": diagram_base64,
        "sql_result": sql_result,
        "rag_context": rag_context,
        "citations": citations
    }
