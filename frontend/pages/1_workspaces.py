import os
from typing import Optional, Dict, List

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "https://lead-profiling-and-enrichment-engine.onrender.com")
API_TOKEN = os.getenv("API_TOKEN", "")


def _headers(token: Optional[str]) -> Dict[str, str]:
    return {"X-API-TOKEN": token} if token else {}


def fetch_workspaces(api_token: Optional[str]) -> List[Dict]:
    try:
        resp = requests.get(f"{API_URL}/api/workspaces", timeout=20, headers=_headers(api_token))
        resp.raise_for_status()
        return resp.json().get("items", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch workspaces: {e}")
        return []


def create_workspace(workspace_id: str, provider: str, keys: Dict[str, str], api_token: Optional[str]):
    payload = {
        "workspace_id": workspace_id,
        "provider": provider,
        "keys": keys,
    }
    try:
        resp = requests.post(f"{API_URL}/api/workspaces", json=payload, timeout=20, headers=_headers(api_token))
        return resp
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to create workspace: {e}")
        return None


def delete_workspace(workspace_id: str, api_token: Optional[str]):
    try:
        resp = requests.delete(f"{API_URL}/api/workspaces/{workspace_id}", timeout=20, headers=_headers(api_token))
        return resp
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to delete workspace: {e}")
        return None


st.set_page_config(page_title="Workspaces - ProspectPulse", layout="wide", page_icon="🏢")

st.title("🏢 Workspaces")
st.caption("Manage API keys and LLM providers per workspace")

with st.sidebar:
    st.header("⚙️ API Configuration")
    api_url = st.text_input("API URL", API_URL, help="Backend API endpoint")
    if api_url != API_URL:
        API_URL = api_url
    api_token = st.text_input("API Token", value=API_TOKEN, type="password", 
                             help="Optional API token for authentication")

# Main content
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🆕 Create Workspace")
    
    with st.form("create_workspace_form"):
        workspace_id = st.text_input("Workspace ID", placeholder="e.g., production-workspace", 
                                   help="Unique identifier for this workspace")
        
        provider = st.selectbox(
            "LLM Provider", 
            options=["openai", "gemini"], 
            help="Choose which LLM provider to use for this workspace"
        )
        
        st.write("**🔑 API Keys**")
        openai_key = st.text_input("OpenAI API Key", type="password", 
                                 help="Required if provider is OpenAI")
        gemini_key = st.text_input("Gemini API Key", type="password", 
                                 help="Required if provider is Gemini")
        tavily_key = st.text_input("Tavily API Key (Optional)", type="password",
                                 help="For web search capabilities")
        
        submitted = st.form_submit_button("💾 Save Workspace", type="primary", use_container_width=True)
        
        if submitted:
            if not workspace_id:
                st.error("❌ Workspace ID is required")
            elif provider == "openai" and not openai_key:
                st.error("❌ OpenAI API key is required for OpenAI provider")
            elif provider == "gemini" and not gemini_key:
                st.error("❌ Gemini API key is required for Gemini provider")
            else:
                keys = {
                    "provider": provider,
                    "openai_key": openai_key,
                    "gemini_key": gemini_key,
                    "tavily_key": tavily_key,
                }
                
                with st.spinner("Creating workspace..."):
                    resp = create_workspace(workspace_id, provider, keys, api_token)
                    
                if resp.ok:
                    st.success(f"✅ Created workspace: {workspace_id}")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to create workspace: {resp.text}")

with col2:
    st.subheader("📋 Existing Workspaces")
    
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()
    
    workspaces = fetch_workspaces(api_token)
    
    if workspaces:
        for ws in workspaces:
            with st.expander(f"🏢 {ws['id']} ({ws.get('provider', 'N/A')})"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Provider:** {ws.get('provider', 'N/A')}")
                    st.write(f"**Created:** {ws.get('created_at', 'N/A')}")
                    
                    # Show key status (without revealing actual keys)
                    keys = ws.get('api_keys', {})
                    key_status = []
                    if keys.get('openai_key'):
                        key_status.append("🔑 OpenAI")
                    if keys.get('gemini_key'):
                        key_status.append("🔑 Gemini")
                    if keys.get('tavily_key'):
                        key_status.append("🔑 Tavily")
                    
                    st.write(f"**Keys:** {' • '.join(key_status) if key_status else '⚠️ No keys'}")
                
                with col2:
                    if st.button("🔄 Update", key=f"update_{ws['id']}", use_container_width=True):
                        st.info("Update functionality coming soon!")
                
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_{ws['id']}", use_container_width=True):
                        with st.spinner("Deleting workspace..."):
                            resp = delete_workspace(ws['id'], api_token)
                        
                        if resp.ok:
                            st.success(f"✅ Deleted workspace: {ws['id']}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete: {resp.text}")
    
    else:
        st.info("📭 No workspaces found. Create your first workspace to get started.")

# Help section
with st.expander("📖 Help & Tips"):
    st.markdown("""
    **About Workspaces:**
    - Workspaces isolate API keys and LLM configurations
    - Each workspace can use different LLM providers
    - Keys are stored securely in Valkey (server-side)
    
    **Supported Providers:**
    - **OpenAI:** GPT-4o-mini, requires OpenAI API key
    - **Gemini:** Gemini 1.5 Flash, requires Google API key
    
    **Optional Keys:**
    - **Tavily:** For web search and research capabilities
    
    **Best Practices:**
    - Use descriptive workspace IDs (e.g., "production", "development")
    - Keep workspace IDs unique across your organization
    - Regularly rotate API keys for security
    """)
