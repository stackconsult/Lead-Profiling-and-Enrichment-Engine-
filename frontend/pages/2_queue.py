import json
import os
from typing import List, Optional, Dict

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from frontend.components.job_monitor import stream_job

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:10000")
API_TOKEN = os.getenv("API_TOKEN", "")

st.set_page_config(page_title="Queue - ProspectPulse", layout="wide", page_icon="📊")


def _headers(api_token: Optional[str]) -> Dict[str, str]:
    return {"X-API-TOKEN": api_token} if api_token else {}


def fetch_workspaces(api_token: Optional[str]):
    try:
        resp = requests.get(f"{API_URL}/workspaces", timeout=20, headers=_headers(api_token))
        resp.raise_for_status()
        return resp.json().get("items", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch workspaces: {e}")
        return []


def enqueue(leads: List[dict], workspace_id: str, api_token: Optional[str]) -> str:
    resp = requests.post(
        f"{API_URL}/enqueue",
        params={"workspace_id": workspace_id},
        json=leads,
        timeout=30,
        headers=_headers(api_token),
    )
    resp.raise_for_status()
    return resp.json()["job_id"]


def fetch_job_status(job_id: str, api_token: Optional[str]):
    try:
        resp = requests.get(f"{API_URL}/status/{job_id}", headers=_headers(api_token))
        if resp.status_code == 200:
            return resp.json()
        return None
    except:
        return None


def fetch_leads(page: int, size: int, api_token: Optional[str]):
    try:
        resp = requests.get(
            f"{API_URL}/leads",
            params={"page": page, "size": size},
            timeout=20,
            headers=_headers(api_token),
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch leads: {e}")
        return {"items": [], "total": 0}


st.title("📊 Queue & Live Status")
st.caption("Upload leads and monitor processing in real-time")

with st.sidebar:
    st.header("⚙️ Configuration")
    api_url = st.text_input("API URL", API_URL, help="Backend API endpoint")
    if api_url != API_URL:
        API_URL = api_url
    
    api_token = st.text_input("API Token", value=API_TOKEN, type="password",
                             help="Optional API token for authentication")
    
    st.divider()
    
    # Workspace selection
    workspaces = fetch_workspaces(api_token)
    if workspaces:
        workspace_options = {ws["id"]: f"{ws['id']} ({ws.get('provider','N/A')})" for ws in workspaces}
        workspace_id = st.selectbox(
            "Workspace",
            options=list(workspace_options.keys()),
            format_func=lambda k: workspace_options.get(k, k),
            help="Choose workspace for processing"
        )
    else:
        st.warning("No workspaces found. Create one in the Workspaces page.")
        workspace_id = None

# Main content
tab1, tab2 = st.tabs(["📤 Upload & Queue", "🔄 Live Monitoring"])

with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📁 Upload Leads")
        
        uploaded = st.file_uploader(
            "Upload leads CSV", 
            type=["csv"],
            help="CSV should contain 'company' column"
        )
        
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                st.info(f"📋 Loaded {len(df)} leads")
                
                # Column validation
                required_cols = ['company']
                available_cols = [col.lower() for col in df.columns]
                
                if not any(req in available_cols for req in required_cols):
                    st.error(f"❌ CSV must contain one of: {', '.join(required_cols)}")
                    st.write(f"Available columns: {', '.join(df.columns)}")
                else:
                    st.success("✅ CSV format looks good!")
                    st.dataframe(df.head(10), use_container_width=True)
                    
                    # Show column mapping
                    st.write("**Column Mapping:**")
                    for req in required_cols:
                        matches = [col for col in df.columns if col.lower() == req]
                        if matches:
                            st.write(f"✅ {req} → {matches[0]}")
                        else:
                            st.write(f"❌ {req} → Not found")
                    
                    # Enqueue button
                    if st.button("🚀 Enqueue Leads", type="primary", use_container_width=True):
                        if not workspace_id:
                            st.error("❌ Please select a workspace first")
                        else:
                            with st.spinner("Enqueuing leads..."):
                                leads = df.to_dict(orient="records")
                                job_id = enqueue(leads, workspace_id, api_token)
                                st.session_state["job_id"] = job_id
                                st.success(f"✅ Enqueued {len(leads)} leads. Job ID: {job_id}")
            except Exception as e:
                st.error(f"❌ Error reading CSV: {e}")
    
    with col2:
        st.subheader("📈 Recent Jobs")
        
        # Show recent job status
        job_id = st.session_state.get("job_id")
        if job_id:
            st.write(f"**Current Job:** {job_id}")
            
            # Fetch and display status
            status = fetch_job_status(job_id, api_token)
            if status:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Status", status.get("status", "unknown"))
                with col2:
                    progress = status.get("progress", 0)
                    st.metric("Progress", f"{progress:.1%}")
                
                # Progress bar
                if progress > 0:
                    st.progress(progress)
                
                # Additional details
                with st.expander("📊 Job Details"):
                    st.json(status)
            else:
                st.warning("Job status not available")
            
            if st.button("🗑️ Clear Current Job", use_container_width=True):
                st.session_state["job_id"] = None
                st.rerun()
        else:
            st.info("📭 No active jobs. Upload some leads to get started.")

with tab2:
    st.subheader("🔄 Live Monitoring")
    
    job_id = st.session_state.get("job_id")
    
    if not job_id:
        st.warning("📭 No active job to monitor. Upload and enqueue leads first.")
    else:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.write(f"**Monitoring Job:** `{job_id}`")
            
            if st.button("▶️ Start Live Stream", type="primary", use_container_width=True):
                with st.spinner("Connecting to job stream..."):
                    try:
                        messages = stream_job(API_URL, job_id, headers=_headers(api_token))
                        if messages:
                            st.success(f"📡 Received {len(messages)} updates")
                            
                            # Show latest message
                            latest = messages[-1]
                            st.write("**Latest Update:**")
                            st.json(latest)
                            
                            # Show message history
                            with st.expander("📜 Message History"):
                                for i, msg in enumerate(messages):
                                    st.write(f"**Message {i+1}:**")
                                    st.json(msg)
                                    st.divider()
                        else:
                            st.warning("📡 No messages received. Job might be complete or not started.")
                    except Exception as e:
                        st.error(f"❌ Stream error: {e}")
        
        with col2:
            if st.button("🔄 Check Status", use_container_width=True):
                with st.spinner("Fetching status..."):
                    status = fetch_job_status(job_id, api_token)
                    if status:
                        st.json(status)
                    else:
                        st.error("❌ Could not fetch job status")
        
        # Auto-refresh option
        if st.checkbox("🔄 Auto-refresh status (every 5 seconds)"):
            placeholder = st.empty()
            while True:
                status = fetch_job_status(job_id, api_token)
                if status:
                    with placeholder.container():
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Status", status.get("status", "unknown"))
                        with col2:
                            progress = status.get("progress", 0)
                            st.metric("Progress", f"{progress:.1%}")
                        
                        if progress > 0:
                            st.progress(progress)
                        
                        if status.get("status") in ["completed", "failed"]:
                            st.success("✅ Job finished!")
                            break
                else:
                    placeholder.write("Status unavailable...")
                
                import time
                time.sleep(5)

# Results section
st.divider()
st.subheader("📊 Processed Results")

page = st.number_input("Page", min_value=1, value=1, step=1)
size = st.selectbox("Results per page", [10, 25, 50, 100], index=1)

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🔄 Refresh Results", use_container_width=True):
        with st.spinner("Fetching results..."):
            data = fetch_leads(page=page, size=size, api_token=api_token)
            st.session_state["results"] = data

with col2:
    data = st.session_state.get("results", {"items": [], "total": 0})
    if data["items"]:
        if st.button("📥 Export CSV", use_container_width=True):
            df_export = pd.DataFrame(data["items"])
            csv = df_export.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name=f"prospectpulse_results_page_{page}.csv",
                mime="text/csv"
            )

# Display results
data = st.session_state.get("results", {"items": [], "total": 0})
items = data.get("items", [])
total = data.get("total", 0)

if items:
    st.info(f"📊 Showing {len(items)} of {total} results")
    df_results = pd.DataFrame(items)
    st.dataframe(df_results, use_container_width=True)
else:
    st.info("📭 No results yet. Process some leads to see results here.")
