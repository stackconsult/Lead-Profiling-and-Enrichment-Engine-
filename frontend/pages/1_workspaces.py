import os
from typing import Optional, Dict

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:10000")
API_TOKEN = os.getenv("API_TOKEN", "")


def _headers(token: Optional[str]) -> Dict[str, str]:
    return {"X-API-TOKEN": token} if token else {}


st.title("Workspaces")
st.write("Store API keys per workspace. Keys are kept in Valkey (server-side).")

with st.sidebar:
    api_url = st.text_input("API URL", API_URL)
    if api_url:
        API_URL = api_url
    api_token = st.text_input("API Token (optional)", value=API_TOKEN, type="password")

provider = st.selectbox("Provider", options=["openai", "gemini"])
openai_key = st.text_input("OpenAI Key", type="password")
gemini_key = st.text_input("Gemini Key", type="password")
tavily_key = st.text_input("Tavily Key (optional)", type="password")

if st.button("Save workspace", type="primary"):
    payload = {
        "provider": provider,
        "keys": {
            "openai_key": openai_key,
            "gemini_key": gemini_key,
            "tavily_key": tavily_key,
        },
    }
    resp = requests.post(f"{API_URL}/workspaces", json=payload, timeout=20, headers=_headers(api_token))
    if resp.ok:
        st.success(f"Saved workspace {resp.json()['workspace_id']}")
    else:
        st.error(f"Error: {resp.text}")

if st.button("Refresh list"):
    resp = requests.get(f"{API_URL}/workspaces", timeout=20, headers=_headers(api_token))
    if resp.ok:
        st.json(resp.json())
    else:
        st.error(resp.text)
