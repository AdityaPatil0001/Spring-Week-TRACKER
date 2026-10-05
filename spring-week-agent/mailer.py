"""Optional SMTP daily summary delivery."""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send_summary(opportunities: list[dict], insights: list[dict], new_count: int) -> bool:
    required = ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "EMAIL_FROM", "EMAIL_TO"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        return False
    msg = EmailMessage()
    msg["Subject"] = f"Spring Week Finder: {new_count} new finding(s)"
    msg["From"] = os.environ["EMAIL_FROM"]
    msg["To"] = os.environ["EMAIL_TO"]
    lines = [f"New findings today: {new_count}", "", "Spring Week opportunities:"]
    for item in opportunities:
        lines.append(f"• {item.get('company_name')} — {item.get('program_title')} | deadline: {item.get('application_deadline') or 'not listed'} | {item.get('direct_application_url')}")
    lines += ["", "Networking and skills:"]
    for person in insights:
        lines.append(f"• {person.get('person_name')} ({person.get('current_or_past_role')}): technical: {', '.join(person.get('technical_skills', []))}; soft: {', '.join(person.get('soft_skills', []))}; {person.get('profile_url', '')}")
    msg.set_content("\n".join(lines))
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")), timeout=30) as server:
        server.starttls()
        server.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
        server.send_message(msg)
    return True
