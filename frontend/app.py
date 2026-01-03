import json
import os
from typing import List, Optional, Dict

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from components.job_monitor import stream_job

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:10000")
API_TOKEN = os.getenv("API_TOKEN", "")

st.set_page_config(page_title="ProspectPulse", layout="wide")


def _headers(api_token: Optional[str]) -> Dict[str, str]:
    return {"X-API-TOKEN": api_token} if api_token else {}


def fetch_workspaces(api_token: Optional[str]):
    resp = requests.get(f"{API_URL}/workspaces", timeout=20, headers=_headers(api_token))
    resp.raise_for_status()
    return resp.json().get("items", [])


def post_enqueue(leads: List[dict], workspace_id: str, api_token: Optional[str]) -> str:
    resp = requests.post(
        f"{API_URL}/enqueue",
        params={"workspace_id": workspace_id},
        json=leads,
        timeout=30,
        headers=_headers(api_token),
    )
    resp.raise_for_status()
    return resp.json()["job_id"]


def fetch_leads(page: int, size: int = 50, api_token: Optional[str] = None):
    resp = requests.get(
        f"{API_URL}/leads",
        params={"page": page, "size": size},
        timeout=20,
        headers=_headers(api_token),
    )
    resp.raise_for_status()
    return resp.json()


st.title("ProspectPulse – Lead Research Orchestrator")

with st.sidebar:
    st.header("Controls")
    api_url = st.text_input("API URL", API_URL)
    if api_url:
        API_URL = api_url
    api_token = st.text_input("API Token (optional)", value=API_TOKEN, type="password")
    st.markdown("Upload CSV with `company` column.")
    if st.button("Refresh workspaces"):
        st.session_state["workspaces"] = fetch_workspaces(api_token)

workspaces = st.session_state.get("workspaces") or fetch_workspaces(API_TOKEN or None)
workspace_options = {ws["id"]: f"{ws['id']} ({ws.get('provider','')})" for ws in workspaces}
workspace_id = st.selectbox("Workspace", options=list(workspace_options.keys()), format_func=lambda k: workspace_options.get(k, k)) if workspace_options else None

uploaded = st.file_uploader("Upload leads CSV", type=["csv"])
job_id = st.session_state.get("job_id")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Queue")
    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df.head())
        if st.button("Enqueue", type="primary"):
            if not workspace_id:
                st.error("Select a workspace first (create one in the Workspaces page).")
            else:
                leads = df.to_dict(orient="records")
                job_id = post_enqueue(leads, workspace_id, api_token)
                st.session_state["job_id"] = job_id
                st.success(f"Enqueued {len(leads)} leads. Job {job_id}")

    if job_id:
        st.info(f"Tracking job: {job_id}")
        if st.button("Start stream"):
            with st.spinner("Listening for updates..."):
                messages = stream_job(API_URL, job_id, headers=_headers(api_token))
                st.json(messages[-1] if messages else {})

with col2:
    st.subheader("Results")
    page = st.number_input("Page", min_value=1, value=1, step=1)
    if st.button("Refresh"):
        data = fetch_leads(page=page, api_token=api_token)
        items = data.get("items", [])
        if items:
            st.dataframe(pd.DataFrame(items))
        else:
            st.write("No results yet.")
