# Spring Week Finder & Networking Agent

A Streamlit dashboard for discovering Spring Week and Spring Insight programmes with the TinyFish Python SDK, gathering public networking and skills clues, persisting findings in SQLite, appending new findings to a Word report, and optionally emailing a daily digest.

## What it does

- Collects sector, course, year, degree, and target company/keyword criteria.
- Searches employer career pages and the public web through TinyFish and requests structured JSON results.
- Researches publicly indexed professional profiles for relevant education and skills. It does not log in to LinkedIn or access private profiles.
- Keeps scan history, results, and preferences in `data/spring_finder.sqlite3`.
- Appends newly discovered programmes to `reports/spring_week_networking_report.docx`.
- Creates a Google Docs report in the authorized Google account's Drive and appends new findings to it.
- Offers a separately run APScheduler process for daily scans (08:00 in `APP_TIMEZONE`).
- Sends email only when SMTP settings are configured.

## Requirements

- Python 3.11 or newer
- A TinyFish API key from [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys)
- SMTP account credentials if you want daily email

## Installation

From this directory, create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `TINYFISH_API_KEY`. If Streamlit is already open, restart it after changing `.env`. You can also enter the key in the dashboard's **Connect TinyFish** field for the current browser session; that value is not saved to disk. Configure the SMTP fields to enable email; for Gmail use an app password rather than your account password. Keep `.env` private and do not commit it.

## Google Drive report

The app uses Google OAuth to create a Google Doc in the account you authorize. `EMAIL_FROM` controls SMTP only; it does not grant Google Drive access. If you want the Google Doc owned by the sender account, authorize that same Google account. The app checks the authorized Google email against `EMAIL_FROM` when it is set.

1. In Google Cloud Console, create/select a project and enable the Google Docs API.
2. Configure the OAuth consent screen, then create an OAuth Client ID with application type **Desktop app**.
3. Download its JSON and save it as `credentials.json` beside `app.py` (this file is ignored by Git).
4. Install the current dependencies and run the OAuth helper from the project folder:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe google_auth.py
   ```

5. Sign in to the intended Google account and approve the requested access. The app stores a refresh token in `data/google_token.json`, which is ignored by Git.

On the first scan with new findings, the app creates **Spring Week Finder & Networking Report** in that account's Drive. Later scans append new findings to the same document. Set `GOOGLE_DOC_ID` in `.env` if you want to target a specific Google Doc that the authorized account can edit. A local `.docx` download remains available as a second copy.

If you start Streamlit from a different working directory, the app still reads `.env` from the project folder next to `app.py`.

## Run the dashboard

```powershell
streamlit run app.py
```

Open the local URL printed by Streamlit, fill in the profile, save it, and click **Run Agent**. Results and history are stored locally. The generated report can be downloaded in the dashboard.

## Daily monitoring

Enable **Daily automated monitoring** in the dashboard, then keep the scheduler process running in a separate terminal:

```powershell
python scheduler.py
```

The scheduler checks the saved monitoring switch and runs at 08:00 in the configured timezone. For a one-off scheduled scan:

```powershell
python scheduler.py --run-once
```

The scheduler is intentionally a separate process from Streamlit: a production deployment should run it as its own worker/service (or under a process manager) so dashboard reruns do not create duplicate schedules. `--run-once` also makes it easy to connect an external OS scheduler.

## Email configuration

Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`, and `EMAIL_TO` in `.env`. The mailer uses STARTTLS. Missing settings disable sending without preventing the scan. SMTP delivery errors are shown as scan errors; review provider-specific requirements and use an app password/token.

## Project structure

```text
app.py             Streamlit dashboard and interactive scan
agent_spring.py    TinyFish Spring Week search and JSON normalization
agent_linkedin.py  TinyFish public networking/skills research
storage.py         SQLite persistence
exporter.py        Create and append the .docx report
mailer.py          Optional SMTP email summaries
scheduler.py       Standalone daily APScheduler worker
.env.example      Configuration template
```

## Data quality and limitations

TinyFish agents work from current public web content; results can be incomplete or stale. Treat deadlines and eligibility as leads, then confirm them on the linked employer page before applying. The agent requests structured fields and leaves unknown values blank rather than intentionally inventing them, but generated results still need review. LinkedIn may restrict public search results; the networking agent only asks for information exposed on public pages and may return no profiles. API usage, throughput, and access depend on your TinyFish account. Daily scheduling requires the scheduler process to remain running, and scheduled email requires working SMTP credentials.
