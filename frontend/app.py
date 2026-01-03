import json
import os
from typing import List, Optional, Dict

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv
from components.job_monitor import stream_job

load_dotenv()

API_URL = os.getenv("API_URL", "https://lead-profiling-and-enrichment-engine.onrender.com")
API_TOKEN = os.getenv("API_TOKEN", "")

st.set_page_config(page_title="ProspectPulse", layout="wide", page_icon="🎯")


def _headers(api_token: Optional[str]) -> Dict[str, str]:
    return {"X-API-TOKEN": api_token} if api_token else {}


def fetch_workspaces(api_token: Optional[str]):
    try:
        resp = requests.get(f"{API_URL}/api/workspaces", timeout=20, headers=_headers(api_token))
        resp.raise_for_status()
        return resp.json().get("items", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch workspaces: {e}")
        return []


def post_enqueue(leads: List[dict], workspace_id: str, api_token: Optional[str]) -> str:
    resp = requests.post(
        f"{API_URL}/api/enqueue",
        params={"workspace_id": workspace_id},
        json=leads,
        timeout=30,
        headers=_headers(api_token),
    )
    resp.raise_for_status()
    return resp.json()["job_id"]


def fetch_leads(page: int, size: int = 50, api_token: Optional[str] = None):
    try:
        resp = requests.get(
            f"{API_URL}/api/leads",
            params={"page": page, "size": size},
            timeout=20,
            headers=_headers(api_token),
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch leads: {e}")
        return {"items": [], "total": 0}


def check_api_health():
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        return resp.status_code == 200
    except:
        return False


# Initialize session state
if "workspaces" not in st.session_state:
    st.session_state["workspaces"] = []
if "job_id" not in st.session_state:
    st.session_state["job_id"] = None

# Header with API status
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🎯 ProspectPulse")
    st.caption("Lead Research & Enrichment Engine")
with col2:
    if check_api_health():
        st.success("API ✅")
    else:
        st.error("API ❌")

with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Configuration
    api_url = st.text_input("API URL", API_URL, help="Backend API endpoint")
    if api_url != API_URL:
        API_URL = api_url
        st.session_state["workspaces"] = []  # Reset workspaces
    
    api_token = st.text_input("API Token", value=API_TOKEN, type="password", 
                             help="Optional API token for authentication")
    
    st.divider()
    
    # Workspace Management
    st.subheader("🏢 Workspace")
    if st.button("🔄 Refresh Workspaces", use_container_width=True):
        with st.spinner("Loading workspaces..."):
            st.session_state["workspaces"] = fetch_workspaces(api_token)
    
    workspaces = st.session_state.get("workspaces", [])
    if workspaces:
        workspace_options = {ws["id"]: f"{ws['id']} ({ws.get('provider','N/A')})" for ws in workspaces}
        workspace_id = st.selectbox(
            "Select Workspace", 
            options=list(workspace_options.keys()), 
            format_func=lambda k: workspace_options.get(k, k),
            help="Choose workspace for LLM provider and API keys"
        )
    else:
        st.warning("No workspaces found. Create one in the Workspaces page.")
        workspace_id = None
    
    st.divider()
    st.markdown("**💡 Tip:** Upload a CSV with `company` column to get started.")

# Main content area
tab1, tab2, tab3 = st.tabs(["📊 Queue", "📈 Results", "⚙️ Workspaces"])

with tab1:
    st.subheader("📊 Lead Queue")
    
    uploaded = st.file_uploader("📁 Upload leads CSV", type=["csv"], help="CSV must contain 'company' column")
    
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
            st.info(f"📋 Loaded {len(df)} leads")
            
            # Show column mapping helper
            if 'company' not in df.columns.str.lower():
                st.warning("⚠️ CSV should contain a 'company' column. Available columns: " + ", ".join(df.columns))
            
            st.dataframe(df.head(10), use_container_width=True)
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🚀 Enqueue Leads", type="primary", use_container_width=True):
                    if not workspace_id:
                        st.error("❌ Please select a workspace first")
                    else:
                        with st.spinner("Enqueuing leads..."):
                            leads = df.to_dict(orient="records")
                            job_id = post_enqueue(leads, workspace_id, api_token)
                            st.session_state["job_id"] = job_id
                            st.success(f"✅ Enqueued {len(leads)} leads. Job ID: {job_id}")
            with col2:
                if st.button("🗑️ Clear Queue", use_container_width=True):
                    st.session_state["job_id"] = None
                    st.rerun()
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
                    
    # Job monitoring
    job_id = st.session_state.get("job_id")
    if job_id:
        st.divider()
        st.subheader(f"🔄 Monitoring Job: {job_id}")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("▶️ Start Stream", use_container_width=True):
                with st.spinner("Connecting to job stream..."):
                    try:
                        messages = stream_job(API_URL, job_id, headers=_headers(api_token))
                        if messages:
                            latest = messages[-1]
                            st.success(f"✅ Latest update: {latest}")
                    except Exception as e:
                        st.error(f"❌ Stream error: {e}")
        with col2:
            if st.button("🛑 Stop Stream", use_container_width=True):
                st.session_state["job_id"] = None
                st.rerun()
        
        if st.button("🔄 Check Status", use_container_width=True):
            try:
                resp = requests.get(f"{API_URL}/status/{job_id}", headers=_headers(api_token))
                if resp.status_code == 200:
                    st.json(resp.json())
                else:
                    st.error("Job not found")
            except Exception as e:
                st.error(f"Status check failed: {e}")

with tab2:
    st.subheader("📈 Processed Results")
    
    page = st.number_input("Page", min_value=1, value=1, step=1)
    size = st.selectbox("Results per page", [10, 25, 50, 100], index=1)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Refresh Results", use_container_width=True):
            with st.spinner("Fetching results..."):
                data = fetch_leads(page=page, size=size, api_token=api_token)
                st.session_state["results"] = data
    
    with col2:
        if st.button("📥 Export CSV", use_container_width=True):
            data = st.session_state.get("results", {"items": []})
            if data["items"]:
                df_export = pd.DataFrame(data["items"])
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name="prospectpulse_results.csv",
                    mime="text/csv"
                )
    
    # Display results
    data = st.session_state.get("results", {"items": [], "total": 0})
    items = data.get("items", [])
    total = data.get("total", 0)
    
    if items:
        st.info(f"📊 Showing {len(items)} of {total} results")
        
        # Convert to DataFrame for display
        df_results = pd.DataFrame(items)
        
        # Add fit score color coding
        if 'fit_score' in df_results.columns:
            def score_color(score):
                if score >= 80:
                    return "🟢"
                elif score >= 60:
                    return "🟡"
                else:
                    return "🔴"
            
            df_results['score_indicator'] = df_results['fit_score'].apply(score_color)
        
        st.dataframe(df_results, use_container_width=True)
    else:
        st.info("📭 No results yet. Upload and process some leads first.")

with tab3:
    st.subheader("⚙️ Workspace Management")
    st.info("🔧 Workspace management is available in the dedicated Workspaces page. Use the navigation above to access it.")
    
    # Quick workspace status
    workspaces = st.session_state.get("workspaces", [])
    if workspaces:
        st.write("**Current Workspaces:**")
        for ws in workspaces:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"🏢 {ws['id']}")
            with col2:
                st.write(f"🤖 {ws.get('provider', 'N/A')}")
            with col3:
                status = "✅" if ws.get('api_keys') else "⚠️"
                st.write(status)
