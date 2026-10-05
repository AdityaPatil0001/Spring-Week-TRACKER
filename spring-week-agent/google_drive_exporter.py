"""Append newly discovered Spring Week findings to the authorized user's Google Doc."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from storage import get_setting, save_setting

ROOT = Path(__file__).resolve().parent
TOKEN_FILE = ROOT / "data" / "google_token.json"


class GoogleDriveNotConfigured(RuntimeError):
    """Raised when the local Google OAuth flow has not been completed."""


def google_connected() -> bool:
    return TOKEN_FILE.exists() or bool(os.getenv("GOOGLE_TOKEN_JSON"))


def _credentials():
    try:
        from google.auth.transport.requests import Request, AuthorizedSession
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise GoogleDriveNotConfigured("Google API libraries are missing. Run pip install -r requirements.txt.") from exc
    raw = os.getenv("GOOGLE_TOKEN_JSON")
    if raw:
        import json
        creds = Credentials.from_authorized_user_info(json.loads(raw))
    elif TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE))
    else:
        raise GoogleDriveNotConfigured("Google Drive is not connected. Add OAuth credentials.json and run `python google_auth.py`.")
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        if TOKEN_FILE.exists():
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    if not creds.valid:
        raise GoogleDriveNotConfigured("Google authorization expired. Run `python google_auth.py` again.")
    return creds


def _authorized_account(creds) -> str:
    from google.auth.transport.requests import AuthorizedSession
    response = AuthorizedSession(creds).get("https://www.googleapis.com/oauth2/v2/userinfo", timeout=20)
    response.raise_for_status()
    email = str(response.json().get("email", "")).lower()
    smtp_sender = os.getenv("EMAIL_FROM", "").strip().lower()
    if smtp_sender and email and smtp_sender != email:
        raise GoogleDriveNotConfigured(
            f"Google Drive is connected as {email}, but EMAIL_FROM is {smtp_sender}. "
            "Authorize the Google account that owns the sender address, or update EMAIL_FROM."
        )
    return email


def _format_scan(opportunities: list[dict[str, Any]], insights_by_url: dict[str, list[dict[str, Any]]], scanned_at: str) -> str:
    lines = [f"\n\nSPRING WEEK SCAN — {scanned_at}", "=" * 58]
    for item in opportunities:
        lines.extend([
            "",
            f"{item.get('company_name') or 'Company'} — {item.get('program_title') or 'Program'}",
            f"Sector: {item.get('sector') or 'Not listed'}",
            f"Deadline: {item.get('application_deadline') or 'Not listed'}",
            f"Location: {item.get('location') or 'Not listed'}",
            f"Application: {item.get('direct_application_url') or 'Not listed'}",
        ])
        for person in insights_by_url.get(item.get("direct_application_url", ""), []):
            lines.extend([
                f"  Profile: {person.get('person_name') or 'Public profile'} — {person.get('current_or_past_role') or 'Role not listed'}",
                f"  Education: {person.get('education') or 'Not listed'}",
                f"  Technical skills: {', '.join(person.get('technical_skills', [])) or 'Not listed'}",
                f"  Soft skills: {', '.join(person.get('soft_skills', [])) or 'Not listed'}",
                f"  Link: {person.get('profile_url') or 'Not listed'}",
                f"  Evidence: {person.get('evidence_note') or 'Not listed'}",
            ])
    return "\n".join(lines) + "\n"


def append_to_google_doc(opportunities: list[dict[str, Any]], insights_by_url: dict[str, list[dict[str, Any]]], scanned_at: str) -> str:
    """Create the report once, then append each scan. Returns the document URL."""
    if not opportunities:
        return ""
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GoogleDriveNotConfigured("Google API libraries are missing. Run pip install -r requirements.txt.") from exc
    creds = _credentials()
    _authorized_account(creds)
    docs = build("docs", "v1", credentials=creds, cache_discovery=False)
    doc_id = os.getenv("GOOGLE_DOC_ID", "").strip() or get_setting("google_doc_id", "")
    if not doc_id:
        document = docs.documents().create(body={"title": "Spring Week Finder & Networking Report"}).execute()
        doc_id = document["documentId"]
        save_setting("google_doc_id", doc_id)
    docs.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"endOfSegmentLocation": {}, "text": _format_scan(opportunities, insights_by_url, scanned_at)}}]},
    ).execute()
    return f"https://docs.google.com/document/d/{doc_id}/edit"
