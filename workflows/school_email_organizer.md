# School Email Organizer — SOP

## Objective
Automatically identify school-related emails in the Gmail inbox, create draft replies for them, and move them into a "school" label — keeping the inbox clean and school emails organized.

## Prerequisites

### One-Time Setup (Google Cloud Console)
1. Go to https://console.cloud.google.com → create a project named `email-organizer`
2. Enable the Gmail API: APIs & Services → Library → search "Gmail API" → Enable
3. Configure OAuth consent screen:
   - Type: External
   - Add your Gmail address as a Test User
   - Add all four scopes:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.modify`
     - `https://www.googleapis.com/auth/gmail.compose`
     - `https://www.googleapis.com/auth/gmail.labels`
4. Create credentials: APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID → Desktop app
   - Download the JSON file, rename it to `credentials.json`, place it in the project root
5. Get an Anthropic API key from https://console.anthropic.com

### One-Time Setup (Local)
```bash
cd "/Users/chichi/Desktop/email organizer"
pip install -r requirements.txt
```

Edit `.env` and fill in your real `ANTHROPIC_API_KEY`.

## Required Inputs
- `credentials.json` in project root (from Google Cloud Console)
- `ANTHROPIC_API_KEY` in `.env`
- Python dependencies installed (`pip install -r requirements.txt`)

## Configuration (.env)
| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | Anthropic API key |
| `GMAIL_CREDENTIALS_PATH` | `credentials.json` | Path to OAuth credentials |
| `GMAIL_TOKEN_PATH` | `token.json` | Path to cached auth token |
| `SCHOOL_LABEL_NAME` | `school` | Gmail label name for school emails |
| `MAX_EMAILS_TO_FETCH` | `50` | Max unread inbox emails to process per run |
| `CLAUDE_MODEL` | `claude-opus-4-6` | Claude model for classification |

## Running the Pipeline

**Full pipeline (recommended):**
```bash
cd "/Users/chichi/Desktop/email organizer"
python -m tools.run_pipeline
```

**Individual steps (for debugging):**
```bash
python -m tools.fetch_emails      # Step 1: fetch → .tmp/fetched_emails.json
python -m tools.classify_emails   # Step 2: classify → .tmp/classified_emails.json
python -m tools.create_drafts     # Step 3: create Gmail draft replies
python -m tools.label_emails      # Step 4: apply label + archive from inbox
```

## Execution Flow

```
run_pipeline.py
  ↓
fetch_emails.py     [Gmail API: messages.list + messages.get]
  → .tmp/fetched_emails.json
  ↓
classify_emails.py  [Anthropic API: claude-opus-4-6]
  → .tmp/classified_emails.json  {school_emails, other_emails, errors}
  ↓ (if school_emails > 0)
create_drafts.py    [Gmail API: drafts.create]
  → Draft replies created in Gmail Drafts folder
  ↓
label_emails.py     [Gmail API: labels.list/create + messages.modify]
  → "school" label applied, emails removed from INBOX
```

## Expected Outputs
- Gmail left sidebar: "school" label appears with school emails inside
- Gmail Drafts folder: template replies for each school email, ready to edit and send
- `.tmp/classified_emails.json`: full classification log for review

## Personalized Draft Setup (One-Time)

Before drafts will sound like you, run these two commands once to teach the system your writing style:

```bash
# Step 1: Pull your sent emails from Gmail and filter for school-related ones
python -m tools.collect_writing_samples

# Step 2: Have Claude analyze them and generate your style profile
python -m tools.build_style_profile
```

Then open `data/style_profile.md` and edit anything that doesn't sound right — this file is the source of truth. You can also paste additional email examples into `data/manual_samples.txt` (one per section, separated by `---`) and re-run `build_style_profile` to update.

Once `data/style_profile.md` exists, all future pipeline runs will automatically generate personalized drafts in your voice.

## Draft Format

**With style profile** (after one-time setup): Claude generates a complete, ready-to-send draft in your voice using your style guide and a few of your past emails as examples. Open the draft in Gmail, review it, and send.

**Without style profile** (fallback): A generic template is used:
```
Hi [Sender Name],

Thank you for your email regarding "[Subject]".

[Your reply here]

Best regards,
[Your name]
```

## Edge Cases

### No unread emails
Pipeline prints "No unread emails" and exits cleanly. No API calls to Claude are made.

### No school emails found
Pipeline exits after classification step. No drafts created, no labels applied.

### First-time auth (browser window)
On the first run, a browser window opens for Google OAuth. Sign in with your Gmail account and grant all requested permissions. A `token.json` file is saved — future runs skip this step.

### Token expired
`gmail_auth.py` auto-refreshes tokens using the refresh token. If refresh fails (rare), delete `token.json` and run again to re-authenticate.

### Gmail OAuth scope error (403 insufficient permissions)
This means the OAuth consent screen in Google Cloud Console is missing some scopes.
Fix: Add all four scopes → delete `token.json` → run again.

### Claude returns malformed JSON
`classify_emails.py` catches `json.JSONDecodeError`. The affected email is logged in `.tmp/classified_emails.json` under `errors` and skipped. If this happens frequently, check that `CLAUDE_MODEL` is set correctly in `.env`.

### Email has no plain text body (HTML-only)
`fetch_emails.py` recursively searches MIME parts for `text/plain`. If only HTML exists, body will be an empty string. Claude will still classify based on sender and subject — usually sufficient. If this causes misclassification, add an HTML-to-text fallback.

### "school" label already exists
`get_or_create_label()` checks before creating — safe to run multiple times.

### Emails already labeled "school"
`messages.modify()` is idempotent for `addLabelIds`. Running the pipeline twice on the same emails will re-apply the label (no error) and create duplicate drafts. Avoid running the pipeline on already-processed emails.

### Gmail API rate limit (429)
The Gmail API allows 250 quota units per user per second. `messages.get()` costs 5 units each, so 50 emails = 250 units, which is right at the limit.
Fix: Add `import time; time.sleep(0.5)` between `messages.get()` calls in `fetch_emails.py` and update this workflow.

### Anthropic API rate limit
Unlikely for <50 emails. If it happens, add `time.sleep(1)` between calls in `classify_emails.py` and update this workflow.

## Cost Estimate (per run, 50 emails)
- Claude Opus 4.6: ~50 small API calls ≈ $0.05–0.15 depending on email length
- Gmail API: Free within standard quota limits

## Known Constraints
- `MAX_EMAILS_TO_FETCH` capped at 100 to control Claude API costs
- Email body truncated to 3000 chars in fetch step (school signals appear early in emails)
- No draft deduplication — running pipeline twice creates duplicate drafts
- Only processes **unread** emails in the **inbox** (not already-labeled or already-read emails)

## Future Improvements (do not implement unless asked)
- Schedule with cron or launchd for automatic periodic runs
- Draft deduplication by checking existing drafts for same `threadId`
- HTML-to-text fallback for email body extraction
- Confidence threshold filter (e.g., skip "low" confidence classifications)
- Batch Claude API calls to reduce per-email latency
