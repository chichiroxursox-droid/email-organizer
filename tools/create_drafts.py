import base64
import json
import os
import random
import sys
from email.mime.text import MIMEText

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.gmail_auth import get_gmail_service

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, ".env"))

DRAFT_TEMPLATE = """Hi {sender_name},

Thank you for your email regarding "{subject}".

[Your reply here]

Best regards,
[Your name]"""


def load_style_profile():
    """Load the writing style guide from data/style_profile.md. Returns None if not found."""
    path = os.path.join(_project_root, "data", "style_profile.md")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read()


def load_writing_examples(n=3):
    """Load a few writing examples from data/writing_samples.json for few-shot context."""
    path = os.path.join(_project_root, "data", "writing_samples.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        samples = json.load(f)
    # Pick examples that have a body
    with_body = [s for s in samples if s.get("body", "").strip()]
    return random.sample(with_body, min(n, len(with_body)))


def generate_personalized_draft(incoming_email, style_profile, examples):
    """Use Claude to write a full draft reply in the user's style.

    Returns the draft body text as a string.
    """
    # Format few-shot examples
    examples_block = ""
    if examples:
        parts = []
        for ex in examples:
            subj = ex.get("subject", "")
            body = ex.get("body", "").strip()
            parts.append(f"(Subject: {subj})\n{body}")
        examples_block = (
            "\n\nHere are real emails this person has written. "
            "Use these as style reference:\n\n"
            + "\n\n---\n\n".join(parts)
        )

    incoming_subject = incoming_email.get("subject", "(no subject)")
    incoming_from = incoming_email.get("from", "")
    incoming_body = incoming_email.get("body", "").strip()

    prompt = f"""You are writing a draft email reply on behalf of this person. Write the full email — ready to send, no placeholders.

STYLE GUIDE (follow this closely):
{style_profile}
{examples_block}

---

INCOMING EMAIL TO REPLY TO:
From: {incoming_from}
Subject: {incoming_subject}
Body:
{incoming_body[:2000]}

---

Write a complete draft reply in this person's voice. Match their tone, greeting style, length, and sign-off exactly as described in the style guide. Output only the email body — no explanation, no meta-commentary."""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")

    response = client.messages.create(
        model=model,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def extract_sender_name(from_field):
    """Extract display name from 'Name <email@domain.com>' format."""
    if "<" in from_field:
        name = from_field.split("<")[0].strip().strip('"').strip("'")
        return name if name else from_field.split("<")[1].split("@")[0]
    return from_field.split("@")[0]


def extract_sender_email(from_field):
    """Extract email address from 'Name <email@domain.com>' or plain email format."""
    if "<" in from_field:
        return from_field.split("<")[-1].replace(">", "").strip()
    return from_field.strip()


def create_draft_reply(service, email, style_profile=None, examples=None):
    """Create a Gmail draft reply for a single email. Returns the created draft dict."""
    sender_name = extract_sender_name(email["from"])
    sender_email = extract_sender_email(email["from"])

    if style_profile:
        body = generate_personalized_draft(email, style_profile, examples or [])
    else:
        body = DRAFT_TEMPLATE.format(
            sender_name=sender_name,
            subject=email["subject"],
        )

    mime_message = MIMEText(body, "plain", "utf-8")
    mime_message["To"] = sender_email
    mime_message["Subject"] = f"Re: {email['subject']}"

    raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

    draft = service.users().drafts().create(
        userId="me",
        body={
            "message": {
                "raw": raw,
                "threadId": email["thread_id"],
            }
        },
    ).execute()

    return {
        "draft_id": draft["id"],
        "email_id": email["id"],
        "to": sender_email,
        "subject": email["subject"],
    }


def create_all_drafts(school_emails, account_email=None):
    """Create draft replies for a list of school emails.

    account_email: if provided, authenticates as that specific account.
    Returns (drafts_created, errors) lists.
    """
    if not school_emails:
        print("No school emails to create drafts for.")
        return [], []

    service = get_gmail_service(account_email=account_email)
    label = f"[{account_email}] " if account_email else ""

    style_profile = load_style_profile()
    examples = []
    if style_profile:
        examples = load_writing_examples(n=3)
        print(f"{label}Style profile loaded — drafts will be personalized.")
    else:
        print(
            f"{label}No style profile found — using generic template.\n"
            "  Run: python -m tools.collect_writing_samples\n"
            "  Then: python -m tools.build_style_profile"
        )

    print(f"{label}Creating draft replies for {len(school_emails)} school emails...")

    drafts_created = []
    errors = []

    for i, email in enumerate(school_emails, 1):
        try:
            result = create_draft_reply(service, email, style_profile=style_profile, examples=examples)
            drafts_created.append(result)
            print(f"  [{i}/{len(school_emails)}] Draft created: {email['subject'][:60]}")
        except Exception as e:
            errors.append({"email_id": email["id"], "subject": email["subject"], "error": str(e)})
            print(f"  [{i}/{len(school_emails)}] Failed: {email['subject'][:60]} — {e}")

    print(f"\nDrafts created: {len(drafts_created)}, Errors: {len(errors)}")
    return drafts_created, errors


if __name__ == "__main__":
    input_path = os.path.join(_project_root, ".tmp/classified_emails.json")
    if not os.path.exists(input_path):
        print("No classified_emails.json found. Run classify_emails.py first.")
    else:
        with open(input_path) as f:
            data = json.load(f)
        create_all_drafts(data.get("school_emails", []))
