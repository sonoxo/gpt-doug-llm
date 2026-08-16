"""
✓ 5/10 Streamlit Dashboard — Web UI for all 10 agents
Deploy free: streamlit run hackathon/deploy/streamlit_dashboard.py
Or: push to GitHub → share.streamlit.io (free hosting for public repos)
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    import streamlit as st
except ImportError:
    print("Install: pip install streamlit")
    print("Run: streamlit run hackathon/deploy/streamlit_dashboard.py")
    sys.exit(1)

st.set_page_config(page_title="GPT Doug Agents", page_icon="🛰️", layout="wide")
st.title("🛰️ GPT Doug — 10 Agents for Humans")
st.markdown("### https://agentsforhumans.devpost.com/ | https://github.com/sonoxo/gpt-doug-llm")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "🔒 Sentinel", "📄 Contracts", "🥫 Food Bank", "📅 Meetings", "💊 Health",
    "💰 Invoices", "🚨 Emergency", "🔍 Code Review", "💳 Expenses", "🏫 School"
])

with tab1:
    st.header("Agent #1 — Zyra Sentinel Bot")
    if st.button("Run Home Network Scan"):
        from hackathon.agents.sentinel_bot import run_home_scan, format_alert
        r = run_home_scan()
        st.code(format_alert(r))
        if r["internal_findings"]: st.json(r["internal_findings"][:5])

with tab2:
    st.header("Agent #2 — Document Drafter")
    text = st.text_area("Paste contract:", height=150, key="contract")
    if st.button("Review Contract") and text:
        from hackathon.agents.document_drafter import review_contract
        st.json(review_contract(text))

with tab3:
    st.header("Agent #3 — NeighborHelp Bot")
    items_str = st.text_input("Inventory (JSON):", '[{"name":"Rice","quantity":5,"threshold":10}]')
    if st.button("Check Inventory"):
        from hackathon.agents.neighbor_help import check_inventory
        st.json(check_inventory(eval(items_str)))

with tab4:
    st.header("Agent #4 — Meeting Sentinel")
    col1, col2 = st.columns(2)
    with col1:
        new_start = st.text_input("New meeting start", "2026-09-01T10:00:00")
        new_end = st.text_input("New meeting end", "2026-09-01T11:00:00")
    with col2:
        exist_start = st.text_input("Existing meeting start", "2026-09-01T10:30:00")
        exist_end = st.text_input("Existing meeting end", "2026-09-01T11:00:00")
    if st.button("Check Conflict"):
        from hackathon.agents.meeting_sentinel import check_conflict
        r = check_conflict({"title":"New","start":new_start,"end":new_end}, [{"title":"Existing","start":exist_start,"end":exist_end}])
        st.json(r)

with tab5:
    st.header("Agent #5 — Health Tracker")
    meds_str = st.text_input("Medications (JSON):", '[{"name":"Aspirin","next_dose":"2020-01-01T08:00:00"}]')
    if st.button("Check Schedule"):
        from hackathon.agents.health_tracker import check_schedule
        st.json(check_schedule(eval(meds_str)))

with tab6:
    st.header("Agent #6 — Invoice Ninja")
    col1, col2 = st.columns(2)
    with col1: hours = st.number_input("Hours", 40.0)
    with col2: rate = st.number_input("Rate/hr", 75.0)
    if st.button("Generate Invoice"):
        from hackathon.agents.invoice_ninja import generate_invoice
        st.json(generate_invoice("Client", hours, rate, "Development"))

with tab7:
    st.header("Agent #7 — Emergency Mesh")
    if st.button("Check Emergency Feeds"):
        from hackathon.agents.emergency_mesh import check_emergency_feeds
        st.json(check_emergency_feeds())
    if st.button("Test Coordination"):
        from hackathon.agents.emergency_mesh import coordinate_response
        st.json(coordinate_response([{"severity":"CRITICAL","description":"power outage"}], []))

with tab8:
    st.header("Agent #8 — Code Reviewer ★")
    pr_title = st.text_input("PR Title", "Add payment endpoint")
    pr_diff = st.text_area("PR Diff", "api_key = 'sk_test_12345'")
    if st.button("Review PR"):
        from hackathon.agents.code_reviewer import review_pr
        r = review_pr({"number":1,"title":pr_title,"body":"","diff":pr_diff,"files":["api.py"],"author":"test"})
        st.markdown(r["comment"])
        st.json(r)

with tab9:
    st.header("Agent #9 — Expense Sentinel")
    merchant = st.text_input("Merchant", "Amazon")
    amount = st.number_input("Amount", 49.99)
    if st.button("Categorize"):
        from hackathon.agents.expense_sentinel import categorize_expense
        st.json(categorize_expense(merchant, amount))

with tab10:
    st.header("Agent #10 — School Coordinator")
    roles_str = st.text_input("Roles (JSON):", '[{"name":"Setup","required_skills":["lifting"]}]')
    vols_str = st.text_input("Volunteers (JSON):", '[{"name":"Alice","skills":["lifting"],"available":true}]')
    if st.button("Match"):
        from hackathon.agents.school_coordinator import match_volunteers
        st.json(match_volunteers(eval(roles_str), eval(vols_str)))
