"""
Enterprise integrations page for Streamlit frontend.
Manages CRM and enterprise system connections.
"""
from __future__ import annotations

import os
import requests
from typing import Dict, List, Any, Optional
import streamlit as st

API_URL = os.getenv("API_URL", "https://lead-profiling-and-enrichment-engine.onrender.com")

def _headers(api_token: Optional[str]) -> Dict[str, str]:
    return {"X-API-TOKEN": api_token} if api_token else {}

def get_integrations(api_token: Optional[str]) -> List[str]:
    """Get list of configured integrations"""
    try:
        resp = requests.get(f"{API_URL}/api/enterprise/integrations", timeout=20, headers=_headers(api_token))
        resp.raise_for_status()
        return resp.json().get("integrations", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch integrations: {e}")
        return []

def test_all_integrations(api_token: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Test all enterprise integrations"""
    try:
        resp = requests.get(f"{API_URL}/api/enterprise/integrations/test-all", timeout=20, headers=_headers(api_token))
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to test integrations: {e}")
        return {}

def add_integration(name: str, integration_type: str, config: Dict[str, str], api_token: Optional[str]) -> bool:
    """Add a new enterprise integration"""
    try:
        payload = {
            "type": integration_type,
            **config
        }
        resp = requests.post(f"{API_URL}/api/enterprise/integrations/{name}", json=payload, timeout=20, headers=_headers(api_token))
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to add integration: {e}")
        return False

def remove_integration(name: str, api_token: Optional[str]) -> bool:
    """Remove an enterprise integration"""
    try:
        resp = requests.delete(f"{API_URL}/api/enterprise/integrations/{name}", timeout=20, headers=_headers(api_token))
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to remove integration: {e}")
        return False

def sync_leads(integration_name: str, limit: int, api_token: Optional[str]) -> List[Dict[str, Any]]:
    """Sync leads from an integration"""
    try:
        resp = requests.get(f"{API_URL}/api/enterprise/integrations/{integration_name}/leads", params={"limit": limit}, timeout=20, headers=_headers(api_token))
        resp.raise_for_status()
        data = resp.json()
        return data.get("leads", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to sync leads: {e}")
        return []

def enterprise_status(api_token: Optional[str]) -> Dict[str, Any]:
    """Get enterprise integration status"""
    try:
        resp = requests.get(f"{API_URL}/api/enterprise/status", timeout=20, headers=_headers(api_token))
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to get status: {e}")
        return {}

def show_page():
    """Main enterprise integrations page"""
    st.title("🏢 Enterprise Integrations")
    st.markdown("Connect and manage your CRM and enterprise system integrations.")
    
    api_token = st.session_state.get("api_token")
    if not api_token:
        st.error("Please set your API token in the sidebar to access enterprise features.")
        return
    
    # Get current status
    with st.spinner("Loading enterprise status..."):
        status = enterprise_status(api_token)
    
    # Status Overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Integrations", status.get("total_integrations", 0))
    
    with col2:
        st.metric("Active Integrations", status.get("active_integrations", 0))
    
    with col3:
        success_rate = 0
        if status.get("total_integrations", 0) > 0:
            success_rate = (status.get("active_integrations", 0) / status.get("total_integrations", 1)) * 100
        st.metric("Success Rate", f"{success_rate:.1f}%")
    
    st.divider()
    
    # Integration Management
    tab1, tab2, tab3 = st.tabs(["Manage Integrations", "Sync Leads", "Connection Status"])
    
    with tab1:
        st.subheader("🔧 Manage Enterprise Integrations")
        
        # Add new integration
        with st.expander("Add New Integration", expanded=False):
            integration_name = st.text_input("Integration Name", key="new_integration_name")
            integration_type = st.selectbox(
                "Integration Type",
                ["salesforce", "hubspot", "microsoft_dynamics", "sap", "custom"],
                key="new_integration_type"
            )
            
            if integration_type == "salesforce":
                api_key = st.text_input("Salesforce API Key", type="password", key="sf_api_key")
                api_url = st.text_input("Salesforce API URL", key="sf_api_url")
                environment = st.selectbox("Environment", ["production", "sandbox", "development"], key="sf_env")
                
                config = {
                    "api_key": api_key,
                    "api_url": api_url,
                    "environment": environment
                }
            
            elif integration_type == "hubspot":
                api_key = st.text_input("HubSpot API Key", type="password", key="hs_api_key")
                environment = st.selectbox("Environment", ["production", "development"], key="hs_env")
                
                config = {
                    "api_key": api_key,
                    "environment": environment
                }
            
            else:
                st.info("Custom integration configuration coming soon.")
                config = {}
            
            if st.button("Add Integration", type="primary"):
                if integration_name and config:
                    if add_integration(integration_name, integration_type, config, api_token):
                        st.success(f"Integration '{integration_name}' added successfully!")
                        st.rerun()
                else:
                    st.error("Please provide integration name and configuration.")
        
        # List existing integrations
        integrations = get_integrations(api_token)
        
        if integrations:
            st.subheader("📋 Current Integrations")
            
            for integration_name in integrations:
                with st.expander(f"🔗 {integration_name}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Name:** {integration_name}")
                    
                    with col2:
                        if st.button("Remove", key=f"remove_{integration_name}"):
                            if remove_integration(integration_name, api_token):
                                st.success(f"Integration '{integration_name}' removed successfully!")
                                st.rerun()
        else:
            st.info("No enterprise integrations configured. Add your first integration above!")
    
    with tab2:
        st.subheader("📥 Sync Leads from Enterprise Systems")
        
        integrations = get_integrations(api_token)
        
        if integrations:
            integration_name = st.selectbox("Select Integration", integrations, key="sync_integration")
            limit = st.number_input("Number of leads to sync", min_value=1, max_value=1000, value=50, key="sync_limit")
            
            if st.button("Sync Leads", type="primary"):
                with st.spinner(f"Syncing leads from {integration_name}..."):
                    leads = sync_leads(integration_name, limit, api_token)
                
                if leads:
                    st.success(f"Successfully synced {len(leads)} leads!")
                    
                    # Display leads
                    st.dataframe(leads, use_container_width=True)
                    
                    # Download option
                    csv_data = "\n".join([",".join([str(lead.get(k, "")) for k in leads[0].keys()]) for lead in leads])
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name=f"{integration_name}_leads.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No leads found or sync failed.")
        else:
            st.info("No enterprise integrations available for syncing.")
    
    with tab3:
        st.subheader("🔍 Connection Status")
        
        if st.button("Test All Connections", type="primary"):
            with st.spinner("Testing all integrations..."):
                test_results = test_all_integrations(api_token)
            
            if test_results:
                for integration_name, result in test_results.items():
                    status_icon = "✅" if result.get("status") == "success" else "❌"
                    st.write(f"{status_icon} **{integration_name}**: {result.get('message', 'No message')}")
            else:
                st.info("No test results available.")


if __name__ == "__main__":
    show_page()
