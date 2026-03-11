# Gmail Inbox Organizer

An AI-powered Python pipeline that automatically manages your Gmail inbox. It fetches unread emails, classifies them using Claude AI, applies Gmail labels, and drafts personalized replies — all with a single command.

## What It Does

- **Fetches** unread emails from your Gmail inbox via the Gmail API
- **Classifies** each email using Anthropic's Claude (e.g., school, college, other)
- **Labels** emails in Gmail so they're automatically sorted into the right folders
- **Drafts replies** in your own writing voice, ready to review and send

## How It Works

```
fetch_emails → classify_emails → create_drafts → label_emails
```

Each step runs independently, or you can run the full pipeline at once.

## Setup

### 1. Google Cloud Console (one-time)

1. Create a project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable the **Gmail API** (APIs & Services → Library)
3. Configure the OAuth consent screen — add your Gmail address as a Test User with these scopes:
   - `gmail.readonly`, `gmail.modify`, `gmail.compose`, `gmail.labels`
4. Create an **OAuth 2.0 Client ID** (Desktop app) → download the JSON → rename it `credentials.json` → place it in the project root
5. Get an **Anthropic API key** at [console.anthropic.com](https://console.anthropic.com)

### 2. Local Setup

```bash
git clone https://github.com/chichiroxursox-droid/email-organizer.git
cd email-organizer
pip install -r requirements.txt
cp .env.example .env
# Fill in your ANTHROPIC_API_KEY in .env
```

### 3. First Run (Google Auth)

The first time you run the pipeline, a browser window will open for Google OAuth. Sign in and grant permissions. A `token.json` file is saved — future runs skip this step.

## Usage

**Run the full pipeline:**
```bash
python -m tools.run_pipeline
```

**Run individual steps (for debugging):**
```bash
python -m tools.fetch_emails       # Fetch unread emails → .tmp/fetched_emails.json
python -m tools.classify_emails    # Classify with Claude → .tmp/classified_emails.json
python -m tools.create_drafts      # Create draft replies in Gmail
python -m tools.label_emails       # Apply labels + archive from inbox
```

## Personalized Drafts (Optional)

Teach the system your writing style so drafts sound like you wrote them:

```bash
# Step 1: Pull your sent school emails from Gmail
python -m tools.collect_writing_samples

# Step 2: Have Claude analyze them and generate a style profile
python -m tools.build_style_profile
```

Then review and edit `data/style_profile.md`. You can also add more email examples to `data/manual_samples.txt` (separated by `---`) and re-run `build_style_profile` to improve the profile.

Once the style profile exists, all future pipeline runs will use it automatically.

## Configuration

Copy `.env.example` to `.env` and fill in your values:

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `GMAIL_CREDENTIALS_PATH` | `credentials.json` | Path to Google OAuth credentials |
| `GMAIL_ACCOUNTS` | *(required)* | Your Gmail address |
| `SCHOOL_LABEL_NAME` | `school` | Gmail label for school emails |
| `COLLEGE_LABEL_NAME` | `college` | Gmail label for college emails |
| `MAX_EMAILS_TO_FETCH` | `50` | Max emails to process per run |
| `CLAUDE_MODEL` | `claude-opus-4-6` | Claude model to use |

## Project Structure

```
tools/
  gmail_auth.py              # Google OAuth authentication
  fetch_emails.py            # Pulls emails from Gmail API
  classify_emails.py         # Classifies emails using Claude
  label_emails.py            # Applies Gmail labels
  create_drafts.py           # Generates draft replies
  run_pipeline.py            # Runs all steps end-to-end
  collect_writing_samples.py # Fetches sent emails for style learning
  build_style_profile.py     # Builds your writing style profile
workflows/
  school_email_organizer.md  # Full SOP and edge case documentation
data/
  manual_samples.txt         # Paste your own email examples here
.env.example                 # Environment variable template
```

## Cost

Running the pipeline on 50 emails with Claude Opus costs approximately **$0.05–0.15** per run. The Gmail API is free within standard quota limits.

## Requirements

- Python 3.8+
- A Google Cloud project with Gmail API enabled
- An Anthropic API key
