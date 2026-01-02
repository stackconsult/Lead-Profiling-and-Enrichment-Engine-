import json
import os
from typing import List

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from frontend.components.job_monitor import stream_job

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:10000")

st.title("Queue & Live Status")

with st.sidebar:
    st.header("API")
    api_url = st.text_input("API URL", API_URL)
    if api_url:
        API_URL = api_url

uploaded = st.file_uploader("Upload leads CSV", type=["csv"])
job_id = st.session_state.get("job_id")

col1, col2 = st.columns(2)


def enqueue(leads: List[dict]) -> str:
    resp = requests.post(f"{API_URL}/enqueue", json=leads, timeout=30)
    resp.raise_for_status()
    return resp.json()["job_id"]


with col1:
    st.subheader("Queue")
    if uploaded:
        df = pd.read_csv(uploaded)
        st.dataframe(df.head())
        if st.button("Enqueue", type="primary"):
            leads = df.to_dict(orient="records")
            job_id = enqueue(leads)
            st.session_state["job_id"] = job_id
            st.success(f"Enqueued {len(leads)} leads. Job {job_id}")

    if job_id:
        st.info(f"Tracking job: {job_id}")
        if st.button("Start live stream"):
            with st.spinner("Listening for updates..."):
                messages = stream_job(API_URL, job_id)
                if messages:
                    st.json(messages[-1])
                else:
                    st.warning("No messages received.")


with col2:
    st.subheader("Results")
    page = st.number_input("Page", min_value=1, value=1, step=1)
    size = st.selectbox("Page size", options=[25, 50, 100], index=1)

    def fetch_leads(page: int, size: int):
        resp = requests.get(f"{API_URL}/leads", params={"page": page, "size": size}, timeout=20)
        resp.raise_for_status()
        return resp.json()

    if st.button("Refresh results"):
        data = fetch_leads(page=page, size=size)
        items = data.get("items", [])
        if items:
            st.dataframe(pd.DataFrame(items))
        else:
            st.write("No results yet.")
