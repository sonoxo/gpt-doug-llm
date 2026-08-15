"""
FREE deployment: Streamlit Cloud (free hosting for public repos)
Creates a web UI for all 10 GPT Doug agents.

Run locally:  streamlit run hackathon/deploy/streamlit-free.py
Deploy free:  Push to GitHub, connect at share.streamlit.io
"""
import streamlit as st
import sys
import json
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

st.set_page_config(page_title="GPT Doug Agents", page_icon="🛰️", layout="wide")
st.title("🛰️ GPT Doug — 10 Agents for Humans")
st.markdown("**Hackathon:** https://agentsforhumans.devpost.com/")

agent = st.selectbox("Select Agent", [
    "#1 Zyra Sentinel Bot (Everyday)",
    "#2 Document Drafter (Professional)",
    "#3 NeighborHelp Bot (Good Neighbor)",
    "#4 Meeting Sentinel (Everyday)",
    "#5 Health Tracker (Everyday)",
    "#6 Invoice Ninja (Professional)",
    "#7 Emergency Mesh (Good Neighbor)",
    "#8 Code Reviewer (Professional) ★",
    "#9 Expense Sentinel (Everyday)",
    "#10 School Coordinator (Good Neighbor)",
])

if agent.startswith("#1"):
    st.subheader("Zyra Sentinel Bot — Home Network Security")
    if st.button("Run Home Scan"):
        from hackathon.agents.sentinel_bot import run_home_scan, format_alert
        result = run_home_scan()
        st.text(format_alert(result))
        st.json(result["internal_findings"][:5])

elif agent.startswith("#2"):
    st.subheader("Document Drafter — Contract Review")
    text = st.text_area("Paste contract text:", height=200)
    if st.button("Review Contract") and text:
        from hackathon.agents.document_drafter import review_contract
        result = review_contract(text)
        st.json(result)

elif agent.startswith("#8"):
    st.subheader("Doug Code Reviewer ★ — PR Review")
    pr_data = {
        "title": st.text_input("PR Title", "Add payment endpoint"),
        "diff": st.text_area("PR Diff", "api_key = 'sk_test_12345'"),
        "files": ["api.py"],
    }
    if st.button("Review PR"):
        from hackathon.agents.code_reviewer import review_pr
        pr_data.update({"number": 1, "body": "", "author": "test"})
        result = review_pr(pr_data)
        st.markdown(result["comment"])
        st.json(result)
