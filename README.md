# Anthropic Job Watcher

Checks Anthropic's careers page once a day (~5pm ET) for roles matching your
profile, and emails **mkapadia99@gmail.com** only when a NEW matching role
shows up. Runs entirely free on GitHub Actions.

## How the loop works
1. **Trigger**: GitHub Actions cron fires daily.
2. **Act**: Script calls the Claude API with web search enabled to find
   current Anthropic openings.
3. **Observe**: Model returns structured JSON of matching roles.
4. **Compare**: Script diffs today's roles against `state.json` (last run).
5. **Notify**: If there are new roles, sends you an email. If not, stays
   silent — no daily noise.
6. **Persist**: Commits the updated `state.json` back to the repo so
   tomorrow's run knows what you've already seen.

## One-time setup (15 minutes)

### 1. Create the repo
Create a new **private** GitHub repo (e.g. `anthropic-job-watcher`) and push
these files into it:
```
check_roles.py
requirements.txt
state.json
.github/workflows/daily-check.yml
README.md
```

### 2. Get an Anthropic API key
- Go to https://console.anthropic.com → API Keys → Create Key
- Note: this uses the paid API (separate from your claude.ai subscription).
  Cost per run is tiny — a few cents at most per day, since it's one call
  with web search.

### 3. Create a Gmail "App Password" (free, no Twilio needed)
Since Gmail blocks plain-password SMTP login, you need an App Password:
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification if not already on.
3. Go to https://myaccount.google.com/apppasswords
4. Create an app password (choose "Mail" / "Other"), name it e.g. "job-watcher".
5. Copy the 16-character password shown — you'll use this, not your real
   Gmail password.

You can use your own Gmail address as the *sender* (or create a free
throwaway Gmail account just for this bot, which is a common pattern so you
don't put your personal Gmail app password in a script).

### 4. Add GitHub Secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret**

Add these three:
| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your key from step 2 |
| `GMAIL_ADDRESS` | the Gmail address sending the email |
| `GMAIL_APP_PASSWORD` | the 16-character app password from step 3 |

### 5. Test it manually
Go to the **Actions** tab → "Daily Anthropic Job Watcher" → **Run workflow**
(this uses the `workflow_dispatch` trigger built into the workflow file).
Check the run logs to confirm it worked, and check your inbox if any roles
matched.

### 6. Let it run
From here it runs automatically every day at ~5pm ET (both an EDT and EST
cron are scheduled since GitHub Actions cron doesn't understand daylight
saving — see comments in the workflow file).

## Customizing what counts as a "match"
Edit the `PROFILE` block at the top of `check_roles.py` any time your target
roles change — no other code changes needed.

## Notes
- GitHub Actions free tier includes 2,000 minutes/month for private repos —
  this job takes well under a minute a day, so cost is effectively $0.
- If you ever want SMS instead of email, swap the `send_email` function for
  a Twilio call — the diff/state logic stays identical.
