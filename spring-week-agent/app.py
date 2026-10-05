"""Streamlit dashboard for the Spring Week Finder & Networking Agent."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from agent_linkedin import find_networking_insights
from agent_spring import search_spring_weeks
from exporter import REPORT_PATH, append_scan
from storage import add_scan, connect, get_setting, list_insights, list_opportunities, recent_scans, save_insights, save_opportunity, save_setting

PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"
load_dotenv(ENV_FILE)
st.set_page_config(page_title="Spring Week Finder", page_icon="✦", layout="wide")
st.markdown("""
<style>
.stApp {background:#f3f6f5;color:#20343a}
[data-testid="stHeader"] {background:rgba(243,246,245,.9)}
.block-container {max-width:1320px;padding:1.15rem 2rem 2rem}
[data-testid="stSidebar"] {background:#e7efec;border-right:1px solid #d4e1dc}
[data-testid="stSidebar"] > div:first-child {padding-top:1rem}
[data-testid="stMetric"] {background:#fff;border:1px solid #dce7e2;padding:10px 14px;border-radius:12px;box-shadow:0 2px 8px #15332b0a}
[data-testid="stMetricLabel"] {color:#607771;font-size:.78rem}
[data-testid="stMetricValue"] {color:#155c50;font-size:1.55rem}
div[data-testid="stForm"] {background:#fff;padding:14px;border:1px solid #dce7e2;border-radius:14px}
[data-testid="stVerticalBlock"] {gap:.7rem}
div[data-testid="stDataFrame"] {border:1px solid #dce7e2;border-radius:12px;overflow:hidden}
.stButton > button[kind="primary"] {background:#137967;border:1px solid #137967;color:white;border-radius:10px}
.stButton > button {border-radius:9px}
h1 {color:#173e38;letter-spacing:-.035em}
h2,h3 {color:#254e45;letter-spacing:-.02em}
[data-testid="stAlert"] {border-radius:10px}
</style>
""", unsafe_allow_html=True)

st.title("Spring Week Finder")
st.caption("Opportunity discovery · networking research")

# Support both the local .env file and Streamlit's managed secrets. A key typed
# into this field is session-only and is never written to disk.
try:
    configured_key = os.getenv("TINYFISH_API_KEY") or st.secrets.get("TINYFISH_API_KEY", "")
except Exception:
    configured_key = os.getenv("TINYFISH_API_KEY", "")

settings = get_setting("criteria", {})
with st.sidebar:
    st.markdown("### Search profile")
    if not configured_key:
        with st.expander("Connect TinyFish", expanded=True):
            session_key = st.text_input("TinyFish API key", type="password", help="Used only for this browser session. For a permanent local setup, add it to the project's .env file.")
            if session_key.strip():
                configured_key = session_key.strip()
                os.environ["TINYFISH_API_KEY"] = configured_key
                st.caption("Key ready for this session.")
            else:
                st.caption("Add a key here, or copy `.env.example` to `.env`, fill in `TINYFISH_API_KEY`, then restart Streamlit.")
    if not configured_key:
        st.link_button("Get a TinyFish API key", "https://agent.tinyfish.ai/api-keys", use_container_width=True)
    st.divider()
    with st.form("criteria_form"):
        sector = st.selectbox("Sector", ["Investment Banking", "Software Engineering", "Consulting", "Law", "Other / multiple"], index=["Investment Banking", "Software Engineering", "Consulting", "Law", "Other / multiple"].index(settings.get("sector", "Investment Banking")) if settings.get("sector") in ["Investment Banking", "Software Engineering", "Consulting", "Law", "Other / multiple"] else 0)
        course = st.text_input("Course / Major", settings.get("course", ""), placeholder="Computer Science")
        year = st.selectbox("Year of study", ["1st year", "2nd year", "3rd year", "4th year", "Masters", "Other"], index=["1st year", "2nd year", "3rd year", "4th year", "Masters", "Other"].index(settings.get("year", "1st year")) if settings.get("year") in ["1st year", "2nd year", "3rd year", "4th year", "Masters", "Other"] else 0)
        degree = st.text_input("Degree", settings.get("degree", ""), placeholder="BSc")
        keywords = st.text_area("Target keywords / companies", settings.get("keywords", ""), placeholder="Goldman Sachs, JPMorgan, Python, London")
        saved = st.form_submit_button("Save search profile", use_container_width=True)
        if saved:
            save_setting("criteria", {"sector": sector, "course": course, "year": year, "degree": degree, "keywords": keywords})
            st.success("Search profile saved.")
    st.divider()
    daily = st.toggle("Daily automated monitoring", value=bool(get_setting("monitoring_enabled", False)))
    save_setting("monitoring_enabled", daily)
    if daily:
        st.caption("Scheduler checks this setting daily at 08:00 local time. Keep `python scheduler.py` running.")
    else:
        st.caption("Daily runs are paused. Existing findings remain available.")
    st.caption("Configure SMTP in .env to receive daily email summaries.")

criteria = get_setting("criteria", settings)
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    run_clicked = st.button("▶ Run Agent", type="primary", use_container_width=True)
with col2:
    if st.button("↻ Refresh", use_container_width=True):
        st.rerun()

if run_clicked:
    if not criteria:
        st.error("Save your search profile before starting a scan.")
    elif not configured_key:
        st.error("TinyFish API key is missing. Add it under **Connect TinyFish** in the sidebar, or set `TINYFISH_API_KEY` in the project's `.env` file and restart Streamlit.")
    else:
        timezone = ZoneInfo(os.getenv("APP_TIMEZONE", "Europe/London"))
        now = datetime.now(timezone).isoformat(timespec="seconds")
        scan_id = add_scan(now, "running", "Search started")
        status = st.status("Starting TinyFish research…", expanded=True)
        try:
            status.write("Searching employer career pages and public web sources…")
            opportunities = search_spring_weeks(criteria)
            status.write(f"Found {len(opportunities)} candidate opportunities. Scanning public networking profiles…")
            new_items, all_insights, insight_map = [], [], {}
            progress = st.progress(0, text="Researching companies")
            for index, opportunity in enumerate(opportunities):
                if save_opportunity(opportunity, scan_id, now):
                    new_items.append(opportunity)
                people = find_networking_insights(opportunity["company_name"], opportunity["program_title"])
                save_insights(opportunity.get("direct_application_url", ""), people, now)
                all_insights.extend(people)
                insight_map[opportunity.get("direct_application_url", "")] = people
                progress.progress((index + 1) / max(len(opportunities), 1), text=f"Researching {opportunity.get('company_name', 'company')}")
            new_map = {item.get("direct_application_url", ""): insight_map.get(item.get("direct_application_url", ""), []) for item in new_items}
            append_scan(new_items, new_map, now)
            drive_url = ""
            drive_notice = ""
            if new_items:
                from google_drive_exporter import GoogleDriveNotConfigured, append_to_google_doc
                try:
                    drive_url = append_to_google_doc(new_items, new_map, now)
                except GoogleDriveNotConfigured as exc:
                    drive_notice = str(exc)
                except Exception as exc:
                    drive_notice = f"Google Docs update failed: {exc}"
            from mailer import send_summary
            email_sent = send_summary(new_items, all_insights, len(new_items))
            with connect() as db:
                summary = f"{len(opportunities)} opportunities; {len(new_items)} new; email_sent={email_sent}; drive={'updated' if drive_url else 'not connected/failed'}"
                db.execute("UPDATE scans SET status='completed',message=? WHERE id=?", (summary, scan_id))
            suffix = " · Google Doc updated" if drive_url else (" · Google Drive not connected" if drive_notice else "")
            status.update(label=f"Scan complete · {len(opportunities)} opportunities · {len(new_items)} new{suffix}", state="complete", expanded=False)
            if drive_url:
                st.success("Findings appended to the Google Drive report.")
                st.link_button("Open Google Docs report", drive_url)
            elif drive_notice:
                st.info(f"Local Word report updated. Google Drive: {drive_notice}")
        except Exception as exc:
            with connect() as db:
                db.execute("UPDATE scans SET status='failed',message=? WHERE id=?", (str(exc)[:1000], scan_id))
            status.update(label="Scan failed", state="error")
            st.exception(exc)

opportunities = list_opportunities()
insights = list_insights()
scans = recent_scans()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Programs found", len(opportunities))
m2.metric("Networking profiles", len(insights))
m3.metric("New today", sum(1 for x in opportunities if x.get("first_seen", "")[:10] == datetime.now().astimezone().date().isoformat()))
m4.metric("Latest scan", scans[0]["status"].title() if scans else "Not run")

left, right = st.columns([1.6, 1])
with left:
    st.subheader("Spring Week opportunities")
    if opportunities:
        frame = pd.DataFrame(opportunities)
        columns = [c for c in ["company_name", "program_title", "sector", "application_deadline", "location", "direct_application_url", "first_seen"] if c in frame.columns]
        st.dataframe(frame[columns], use_container_width=True, hide_index=True, column_config={"direct_application_url": st.column_config.LinkColumn("Application link"), "first_seen": "First seen"})
    else:
        st.info("No findings yet. Save your profile and run the agent to discover matching programs.")
with right:
    st.subheader("Recent scan activity")
    if scans:
        st.dataframe(pd.DataFrame(scans)[["created_at", "status", "message"]], use_container_width=True, hide_index=True)
    else:
        st.caption("Your scan history will appear here.")

st.subheader("Networking & skills")
if insights:
    cards = st.columns(2)
    for idx, person in enumerate(insights):
        with cards[idx % 2]:
            with st.container(border=True):
                st.markdown(f"**{person.get('person_name') or 'Public profile'}** · {person.get('current_or_past_role') or 'Role not listed'}")
                st.caption(f"Education: {person.get('education') or 'Not listed'}")
                st.write("Technical: " + (", ".join(person.get("technical_skills", [])) or "Not listed"))
                st.write("Soft skills: " + (", ".join(person.get("soft_skills", [])) or "Not listed"))
                if person.get("profile_url"):
                    st.markdown(f"[View public profile]({person['profile_url']})")
else:
    st.caption("Publicly visible candidate and employee insights will appear after a scan.")

with st.expander("Word report"):
    st.write(f"Report path: `{REPORT_PATH}`")
    if REPORT_PATH.exists():
        st.download_button("Download report (.docx)", REPORT_PATH.read_bytes(), file_name=REPORT_PATH.name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

with st.expander("Google Drive report setup"):
    st.write("Authorize the Google account that owns the Drive report. If you use email summaries, this should match `EMAIL_FROM`.")
    st.code("1. Enable Google Docs API in a Google Cloud project\n2. Create an OAuth Client ID (Desktop app) and save its JSON as credentials.json beside app.py\n3. Run: .venv\\Scripts\\python.exe google_auth.py\n4. Approve access in the browser, then restart Streamlit", language="text")
    st.caption("The first scan creates a Google Doc. Later scans append new findings to that same document.")
