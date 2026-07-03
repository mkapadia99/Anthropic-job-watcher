"""
Anthropic Job Watcher
----------------------
Checks Anthropic's careers page daily for roles matching a target profile,
compares against the last known list (state.json), and emails a notification
only when NEW matching roles appear.

This is the "loop" in loop engineering:
  /goal    -> find new, profile-relevant Anthropic job postings
  /routine -> web search -> extract structured list -> diff vs prior state -> notify
  state    -> state.json (committed back to the repo each run)
"""

import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

import anthropic

STATE_FILE = Path(__file__).parent / "state.json"

# ---- Profile used to judge relevance -----------------------------------
# Edit this block any time your target roles shift.
PROFILE = """
Candidate profile:
- 21+ years engineering leadership experience, currently Director of Quality
  Engineering leading a ~40-person org at a large financial institution.
- Pivoting toward AI-adjacent leadership roles.
- Target role families (in priority order):
  1. Director/VP, AI Platform Engineering
  2. Head of Quality Engineering for AI/ML systems
  3. AI Transformation Lead / AI Program Lead
  4. Director/VP Engineering roles with explicit AI, ML, or agent platform scope
  5. Solutions Architect or Engineering Manager roles focused on AI/ML infra
    (only if senior/leadership-track, not hands-on IC roles)
- NOT a fit: individual contributor research scientist roles, entry/mid-level
  SWE roles, roles unrelated to AI/ML/platform/quality leadership.
"""

SYSTEM_PROMPT = f"""You are a job-matching assistant. You will search Anthropic's
public careers page and identify current open roles that match the candidate
profile below. Use web search to find the live listings at
https://www.anthropic.com/careers (or their ATS-hosted careers site, e.g.
job-boards.greenhouse.io/anthropic) — do not rely on memory, since listings
change daily.

{PROFILE}

Return ONLY valid JSON (no markdown fences, no prose) in this exact shape:
{{
  "roles": [
    {{"title": "...", "team": "...", "location": "...", "url": "...", "why_match": "..."}}
  ]
}}

Only include roles that are a genuine match to the profile's priority list.
If you find no matching roles, return {{"roles": []}}.
"""


def fetch_current_roles(client: anthropic.Anthropic) -> list[dict]:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": "Find current Anthropic job openings matching the profile.",
            }
        ],
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
    )

    # Concatenate all text blocks (web search responses can span multiple blocks)
    text_parts = [block.text for block in response.content if block.type == "text"]
    raw = "".join(text_parts).strip()

    # Defensive cleanup in case the model wraps JSON in fences anyway
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw)
        return data.get("roles", [])
    except json.JSONDecodeError:
        print("WARNING: could not parse model output as JSON:", raw, file=sys.stderr)
        return []


def load_previous_roles() -> list[dict]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text()).get("roles", [])
    return []


def save_current_roles(roles: list[dict]) -> None:
    STATE_FILE.write_text(json.dumps({"roles": roles}, indent=2))


def diff_new_roles(previous: list[dict], current: list[dict]) -> list[dict]:
    seen_urls = {r.get("url") for r in previous}
    return [r for r in current if r.get("url") not in seen_urls]


def send_email(new_roles: list[dict]) -> None:
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    notify_to = os.environ.get("NOTIFY_EMAIL", "mkapadia99@gmail.com")

    lines = ["New Anthropic roles matching your profile:\n"]
    for r in new_roles:
        lines.append(f"- {r.get('title')} ({r.get('team', 'n/a')}, {r.get('location', 'n/a')})")
        lines.append(f"  Why it matches: {r.get('why_match', 'n/a')}")
        lines.append(f"  Link: {r.get('url')}\n")

    body = "\n".join(lines)

    msg = MIMEText(body)
    msg["Subject"] = f"Anthropic Job Watcher: {len(new_roles)} new matching role(s)"
    msg["From"] = gmail_address
    msg["To"] = notify_to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [notify_to], msg.as_string())

    print(f"Email sent to {notify_to} with {len(new_roles)} new role(s).")


def main():
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    current_roles = fetch_current_roles(client)
    previous_roles = load_previous_roles()
    new_roles = diff_new_roles(previous_roles, current_roles)

    print(f"Current matching roles: {len(current_roles)}")
    print(f"New roles since last run: {len(new_roles)}")

    if new_roles:
        send_email(new_roles)
    else:
        print("No new roles. No email sent.")

    save_current_roles(current_roles)


if __name__ == "__main__":
    main()
