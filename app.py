"""
Lead Profiling and Enrichment Engine - Streamlit Application
Main entry point for the Streamlit app
"""

import streamlit as st
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Lead Profiling & Enrichment Engine",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🎯 Lead Profiling and Enrichment Engine")
    st.markdown("""
    ### Welcome to the Lead Profiling and Enrichment Engine
    
    Add leads, let the backend automation engine research, profile and grade them 
    so you understand them better than they understand themselves. 
    Then start connecting and making sales.
    """)
    
    # Placeholder for main content
    st.info("👋 Ready to import your enyir project code here!")
    
    with st.expander("📋 Next Steps"):
        st.markdown("""
        1. Add your enyir project code to this repository
        2. Import the necessary modules in this file
        3. Build your Streamlit UI components
        4. Configure environment variables in `.env`
        5. Deploy to Streamlit Cloud
        """)
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        st.markdown("---")
        st.markdown("**Status:** Ready for Setup")


if __name__ == "__main__":
    main()
