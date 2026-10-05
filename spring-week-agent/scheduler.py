"""Standalone APScheduler process for daily scans. Run separately from Streamlit."""
from __future__ import annotations

import argparse
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from agent_linkedin import find_networking_insights
from agent_spring import search_spring_weeks
from exporter import append_scan
from mailer import send_summary
from storage import add_scan, get_setting, save_insights, save_opportunity


def run_daily_scan() -> dict:
    if not get_setting("monitoring_enabled", False):
        return {"skipped": "Daily monitoring is disabled in the dashboard."}
    criteria = get_setting("criteria", {})
    if not criteria:
        raise RuntimeError("No saved search criteria. Open the dashboard and save criteria first.")
    now = datetime.now(ZoneInfo(os.getenv("APP_TIMEZONE", "Europe/London"))).isoformat(timespec="seconds")
    scan_id = add_scan(now, "running")
    found, insights, insight_map = [], [], {}
    try:
        opportunities = search_spring_weeks(criteria)
        for opportunity in opportunities:
            is_new = save_opportunity(opportunity, scan_id, now)
            if is_new:
                found.append(opportunity)
            people = find_networking_insights(opportunity["company_name"], opportunity["program_title"])
            save_insights(opportunity.get("direct_application_url", ""), people, now)
            insights.extend(people)
            insight_map[opportunity.get("direct_application_url", "")] = people
        new_map = {item.get("direct_application_url", ""): insight_map.get(item.get("direct_application_url", ""), []) for item in found}
        append_scan(found, new_map, now)
        drive_status = "not configured"
        if found:
            from google_drive_exporter import GoogleDriveNotConfigured, append_to_google_doc
            try:
                append_to_google_doc(found, new_map, now)
                drive_status = "updated"
            except GoogleDriveNotConfigured as exc:
                drive_status = str(exc)
            except Exception as exc:
                drive_status = f"update failed: {exc}"
        email_sent = send_summary(found, insights, len(found))
        from storage import connect
        with connect() as db:
            db.execute("UPDATE scans SET status='completed', message=? WHERE id=?", (f"{len(opportunities)} opportunities; {len(found)} new; email_sent={email_sent}; Google Drive: {drive_status}", scan_id))
        return {"opportunities": len(opportunities), "new": len(found), "email_sent": email_sent}
    except Exception as exc:
        from storage import connect
        with connect() as db:
            db.execute("UPDATE scans SET status='failed', message=? WHERE id=?", (str(exc)[:1000], scan_id))
        raise


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-once", action="store_true", help="Run one scan now and exit")
    args = parser.parse_args()
    if args.run_once:
        print(run_daily_scan())
        return
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    tz = ZoneInfo(os.getenv("APP_TIMEZONE", "Europe/London"))
    scheduler = BlockingScheduler(timezone=tz)
    scheduler.add_job(run_daily_scan, CronTrigger(hour=8, minute=0, timezone=tz), id="daily_spring_week_scan", replace_existing=True, coalesce=True, max_instances=1)
    print(f"Daily Spring Week scan scheduled for 08:00 ({tz}). Ctrl+C to stop.")
    scheduler.start()


if __name__ == "__main__":
    main()
