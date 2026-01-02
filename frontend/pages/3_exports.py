import csv
import io
import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:10000")

st.title("Exports")
st.write("Download processed leads as CSV.")

with st.sidebar:
    api_url = st.text_input("API URL", API_URL)
    if api_url:
        API_URL = api_url


def fetch_all() -> list[dict]:
    page = 1
    size = 200
    items: list[dict] = []
    while True:
        resp = requests.get(f"{API_URL}/leads", params={"page": page, "size": size}, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("items", [])
        if not batch:
            break
        items.extend(batch)
        if len(batch) < size:
            break
        page += 1
    return items


if st.button("Download CSV"):
    with st.spinner("Fetching leads..."):
        items = fetch_all()
        if not items:
            st.warning("No leads found.")
        else:
            df = pd.DataFrame(items)
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            st.download_button(
                label="Save CSV",
                data=buf.getvalue(),
                file_name="prospectpulse-leads.csv",
                mime="text/csv",
            )
