import csv
import io
import os
from typing import Optional, Dict, List

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:10000")
API_TOKEN = os.getenv("API_TOKEN", "")

st.set_page_config(page_title="Exports - ProspectPulse", layout="wide", page_icon="📥")


def _headers(api_token: Optional[str]) -> Dict[str, str]:
    return {"X-API-TOKEN": api_token} if api_token else {}


def fetch_all(api_token: Optional[str]) -> List[dict]:
    """Fetch all leads with pagination"""
    page = 1
    size = 200
    items: List[dict] = []
    
    with st.spinner(f"Fetching page {page}..."):
        while True:
            try:
                resp = requests.get(
                    f"{API_URL}/leads", 
                    params={"page": page, "size": size}, 
                    timeout=20,
                    headers=_headers(api_token)
                )
                resp.raise_for_status()
                data = resp.json()
                batch = data.get("items", [])
                
                if not batch:
                    break
                    
                items.extend(batch)
                st.info(f"📊 Fetched {len(items)} leads so far...")
                
                if len(batch) < size:
                    break
                    
                page += 1
            except requests.exceptions.RequestException as e:
                st.error(f"Error fetching page {page}: {e}")
                break
    
    return items


def fetch_filtered(filters: Dict, api_token: Optional[str]) -> List[dict]:
    """Fetch leads with filters (placeholder for future enhancement)"""
    # For now, just fetch all and filter locally
    all_items = fetch_all(api_token)
    
    filtered_items = all_items
    
    # Filter by fit score
    min_score = filters.get('min_fit_score')
    if min_score:
        filtered_items = [item for item in filtered_items 
                         if item.get('fit_score', 0) >= min_score]
    
    # Filter by company name
    company_filter = filters.get('company_filter', '').lower()
    if company_filter:
        filtered_items = [item for item in filtered_items 
                         if company_filter in item.get('company', '').lower()]
    
    return filtered_items


st.title("📥 Exports")
st.caption("Download and export processed leads with custom filters")

with st.sidebar:
    st.header("⚙️ Configuration")
    api_url = st.text_input("API URL", API_URL, help="Backend API endpoint")
    if api_url != API_URL:
        API_URL = api_url
    
    api_token = st.text_input("API Token", value=API_TOKEN, type="password",
                             help="Optional API token for authentication")

# Main content
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🔍 Export Filters")
    
    with st.form("export_filters"):
        st.write("**Score Filtering**")
        min_fit_score = st.slider(
            "Minimum Fit Score",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
            help="Only include leads with fit score >= this value"
        )
        
        st.write("**Company Filtering**")
        company_filter = st.text_input(
            "Company Name Filter",
            placeholder="Partial company name...",
            help="Filter by company name (case-insensitive)"
        )
        
        st.write("**Export Options**")
        include_raw_signals = st.checkbox("Include Raw Signals", value=True)
        include_tech_stack = st.checkbox("Include Tech Stack", value=True)
        include_risks = st.checkbox("Include Risks", value=True)
        
        export_format = st.selectbox(
            "Export Format",
            options=["CSV", "JSON", "Excel"],
            help="Choose export file format"
        )
        
        submitted = st.form_submit_button("📥 Generate Export", type="primary", use_container_width=True)

with col2:
    st.subheader("📊 Export Preview")
    
    if submitted:
        filters = {
            'min_fit_score': min_fit_score,
            'company_filter': company_filter
        }
        
        with st.spinner("Fetching and filtering leads..."):
            items = fetch_filtered(filters, api_token)
        
        if not items:
            st.warning("📭 No leads found matching your criteria.")
        else:
            st.success(f"✅ Found {len(items)} leads matching your filters")
            
            # Show preview
            preview_df = pd.DataFrame(items[:10])
            st.write("**Preview (first 10 results):**")
            st.dataframe(preview_df, use_container_width=True)
            
            # Prepare export data
            export_data = []
            for item in items:
                export_item = {
                    'company': item.get('company', ''),
                    'fit_score': item.get('fit_score', 0),
                    'wedge': item.get('wedge', ''),
                    'approach': item.get('approach', ''),
                    'risk_level': item.get('risk_level', ''),
                }
                
                if include_tech_stack:
                    export_item['tech_stack'] = ', '.join(item.get('tech_stack', []))
                
                if include_risks:
                    export_item['risks'] = ', '.join(item.get('risks', []))
                
                if include_raw_signals:
                    export_item['signals'] = ', '.join(item.get('signals', []))
                
                export_data.append(export_item)
            
            # Generate download
            export_df = pd.DataFrame(export_data)
            
            if export_format == "CSV":
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name=f"prospectpulse_export_{len(items)}_leads.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            elif export_format == "JSON":
                json_data = export_df.to_json(orient='records', indent=2)
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_data,
                    file_name=f"prospectpulse_export_{len(items)}_leads.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            elif export_format == "Excel":
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    export_df.to_excel(writer, index=False, sheet_name='Leads')
                    
                    # Add summary sheet
                    summary_data = {
                        'Metric': ['Total Leads', 'Avg Fit Score', 'High Fit Leads (80+)', 'Medium Fit Leads (60-79)', 'Low Fit Leads (<60)'],
                        'Value': [
                            len(items),
                            f"{export_df['fit_score'].mean():.1f}" if not export_df.empty else "0",
                            len(export_df[export_df['fit_score'] >= 80]),
                            len(export_df[(export_df['fit_score'] >= 60) & (export_df['fit_score'] < 80)]),
                            len(export_df[export_df['fit_score'] < 60])
                        ]
                    }
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, index=False, sheet_name='Summary')
                
                st.download_button(
                    label="⬇️ Download Excel",
                    data=output.getvalue(),
                    file_name=f"prospectpulse_export_{len(items)}_leads.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# Quick export section
st.divider()
st.subheader("⚡ Quick Export")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📊 Export All Leads", use_container_width=True):
        with st.spinner("Fetching all leads..."):
            all_items = fetch_all(api_token)
        
        if all_items:
            df = pd.DataFrame(all_items)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download All CSV",
                data=csv,
                file_name=f"prospectpulse_all_leads_{len(all_items)}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("No leads found")

with col2:
    if st.button("🎯 Export High Fit Only", use_container_width=True):
        filters = {'min_fit_score': 80}
        high_fit_items = fetch_filtered(filters, api_token)
        
        if high_fit_items:
            df = pd.DataFrame(high_fit_items)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download High Fit CSV",
                data=csv,
                file_name=f"prospectpulse_high_fit_{len(high_fit_items)}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("No high-fit leads found")

with col3:
    if st.button("📈 Export Summary Stats", use_container_width=True):
        with st.spinner("Generating summary..."):
            all_items = fetch_all(api_token)
        
        if all_items:
            df = pd.DataFrame(all_items)
            
            # Create summary statistics
            summary_stats = {
                'total_leads': len(all_items),
                'avg_fit_score': df['fit_score'].mean() if 'fit_score' in df.columns else 0,
                'high_fit_count': len(df[df['fit_score'] >= 80]) if 'fit_score' in df.columns else 0,
                'companies_processed': df['company'].nunique() if 'company' in df.columns else 0,
            }
            
            summary_json = pd.Series(summary_stats).to_json(indent=2)
            st.download_button(
                label="⬇️ Download Summary JSON",
                data=summary_json,
                file_name="prospectpulse_summary_stats.json",
                mime="application/json",
                use_container_width=True
            )
        else:
            st.warning("No data available for summary")

# Statistics section
st.divider()
st.subheader("📈 Database Statistics")

if st.button("🔄 Refresh Stats", use_container_width=False):
    with st.spinner("Calculating statistics..."):
        all_items = fetch_all(api_token)
    
    if all_items:
        df = pd.DataFrame(all_items)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Leads", len(all_items))
        
        with col2:
            avg_score = df['fit_score'].mean() if 'fit_score' in df.columns else 0
            st.metric("Avg Fit Score", f"{avg_score:.1f}")
        
        with col3:
            high_fit = len(df[df['fit_score'] >= 80]) if 'fit_score' in df.columns else 0
            st.metric("High Fit (80+)", high_fit)
        
        with col4:
            companies = df['company'].nunique() if 'company' in df.columns else 0
            st.metric("Unique Companies", companies)
        
        # Score distribution chart
        if 'fit_score' in df.columns:
            st.write("**Fit Score Distribution:**")
            score_hist = df['fit_score'].hist(bins=10, alpha=0.7)
            st.bar_chart(score_hist.value_counts().sort_index())
    else:
        st.info("📭 No data available")
