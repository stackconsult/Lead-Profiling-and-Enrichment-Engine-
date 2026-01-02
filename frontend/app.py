import json
import os
from typing import List

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from components.job_monitor import stream_job

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:10000")

st.set_page_config(page_title="ProspectPulse", layout="wide")


def post_enqueue(leads: List[dict]) -> str:
    resp = requests.post(f"{API_URL}/enqueue", json=leads, timeout=30)
    resp.raise_for_status()
    return resp.json()["job_id"]


def fetch_leads(page: int, size: int = 50):
    resp = requests.get(f"{API_URL}/leads", params={"page": page, "size": size}, timeout=20)
    resp.raise_for_status()
    return resp.json()


st.title("ProspectPulse – Lead Research Orchestrator")

with st.sidebar:
    st.header("Controls")
    api_url = st.text_input("API URL", API_URL)
    if api_url:
        API_URL = api_url
    st.markdown("Upload CSV with `company` column.")

uploaded = st.file_uploader("Upload leads CSV", type=["csv"])
job_id = st.session_state.get("job_id")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Queue")
    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df.head())
        if st.button("Enqueue", type="primary"):
            leads = df.to_dict(orient="records")
            job_id = post_enqueue(leads)
            st.session_state["job_id"] = job_id
            st.success(f"Enqueued {len(leads)} leads. Job {job_id}")

    if job_id:
        st.info(f"Tracking job: {job_id}")
        if st.button("Start stream"):
            with st.spinner("Listening for updates..."):
                messages = stream_job(API_URL, job_id)
                st.json(messages[-1] if messages else {})

with col2:
    st.subheader("Results")
    page = st.number_input("Page", min_value=1, value=1, step=1)
    if st.button("Refresh"):
        data = fetch_leads(page=page)
        items = data.get("items", [])
        if items:
            st.dataframe(pd.DataFrame(items))
        else:
            st.write("No results yet.")
