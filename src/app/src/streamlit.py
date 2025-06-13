import streamlit as st
import requests
import json
import pandas as pd

st.set_page_config(page_title="OCI Generative Agent Chat")
st.title("OCI Generative Agent Chat")
st.caption("Ask anything like: 'Show ticket 1052'")

if "session_id" not in st.session_state:
    resp = requests.get("http://localhost:8000/session")
    st.session_state.session_id = resp.json().get("session_id")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with st.form("chat_form"):
    user_input = st.text_input("Ask the agent something...")
    submit = st.form_submit_button("Send")

if submit and user_input.strip():
    with st.spinner("Thinking..."):
        params = {
            "question": user_input,
            "session_id": st.session_state.session_id
        }
        resp = requests.post("http://localhost:8000/chat", json=params)
        data = resp.json()
        reply = data["answer"]

        try:
            parsed = json.loads(reply)
            if "executionResult" in parsed:
                st.write("**Generated Query:**")
                st.code(parsed.get("generatedQuery", ""), language="sql")
                st.write("**Result:**")
                df = pd.DataFrame(parsed["executionResult"])
                st.dataframe(df)
                reply = ""  # Avoid showing raw reply
        except:
            pass

        st.session_state.chat_history.append(("You", user_input))
        st.session_state.chat_history.append(("Agent", reply))

st.markdown("## Chat History")
for sender, msg in st.session_state.chat_history[::-1]:
    st.markdown(f"**{sender}:**")
    st.markdown(msg)
