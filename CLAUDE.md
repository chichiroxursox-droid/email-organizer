# Email Organizer

## What This Is
Automates Gmail inbox management — fetches emails, classifies them using Anthropic's Claude API, applies labels, and drafts responses.

## How It Works
1. Authenticate with Gmail via Google OAuth
2. Fetch unread/recent emails
3. Classify emails by category using Anthropic Claude
4. Apply Gmail labels based on classification
5. Optionally draft responses

## Tools
- `tools/gmail_auth.py` — Google OAuth authentication for Gmail
- `tools/fetch_emails.py` — Pulls emails from Gmail API
- `tools/classify_emails.py` — Sends emails to Anthropic for categorization
- `tools/label_emails.py` — Applies Gmail labels based on classification
- `tools/create_drafts.py` — Generates draft replies (personalized if style profile exists)
- `tools/run_pipeline.py` — Runs the full pipeline end-to-end
- `tools/collect_writing_samples.py` — Fetches sent school emails from Gmail for style learning
- `tools/build_style_profile.py` — Analyzes writing samples and generates `data/style_profile.md`

## APIs & Credentials
- **Google Gmail API** — Email access (OAuth via credentials.json/token.json)
- **Anthropic** — Email classification (key: `ANTHROPIC_API_KEY`)

## Workflows
- `workflows/school_email_organizer.md` — SOP for the school email pipeline

## Writing Style Setup (One-Time)
Run these once to teach the system your writing voice:
```bash
python -m tools.collect_writing_samples   # pulls your sent school emails
python -m tools.build_style_profile       # generates data/style_profile.md
```
Then review and edit `data/style_profile.md`. After that, all drafts are personalized automatically.
You can add more examples anytime to `data/manual_samples.txt` and re-run `build_style_profile`.

## Future Goals
- **Run automatically every morning** — Pipeline should trigger when I wake up my Mac so my inbox is already organized by the time I look at it.

## Current Status
Full pipeline built and functional. Writing style learning is implemented — run the one-time setup above to activate personalized drafts.
