"""Authorize the Google account whose Drive should receive the report."""
from __future__ import annotations

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parent
CLIENT_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "data" / "google_token.json"
SCOPES = ["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/userinfo.email"]


def main() -> None:
    if not CLIENT_FILE.exists():
        raise SystemExit("Download an OAuth Desktop app client JSON from Google Cloud, save it beside this script as credentials.json, then run this command again.")
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print(f"Google authorization saved to {TOKEN_FILE}")
    print("The first Spring Week scan will create the report document in this Google account's Drive.")


if __name__ == "__main__":
    main()
