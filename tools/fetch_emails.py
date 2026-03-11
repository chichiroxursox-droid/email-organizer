import base64
import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.gmail_auth import get_gmail_service

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, ".env"))


def extract_body(payload):
    """Recursively extract plain text body from MIME payload parts."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return ""

    for part in payload.get("parts", []):
        result = extract_body(part)
        if result:
            return result

    return ""


def fetch_unread_emails(max_results=50, account_email=None):
    """Fetch unread emails from Gmail inbox.

    account_email: if provided, authenticates as that specific account.
    Returns a list of dicts with: id, thread_id, from, to, subject, date, body, label_ids.
    Body is truncated to 3000 chars to keep Claude API costs reasonable.
    """
    service = get_gmail_service(account_email=account_email)

    label = f"[{account_email}] " if account_email else ""
    print(f"{label}Fetching up to {max_results} unread inbox emails...")
    results = service.users().messages().list(
        userId="me",
        labelIds=["INBOX", "UNREAD"],
        maxResults=max_results,
    ).execute()

    message_refs = results.get("messages", [])
    if not message_refs:
        print(f"{label}No unread messages found in inbox.")
        return []

    emails = []
    for i, msg_ref in enumerate(message_refs, 1):
        try:
            msg = service.users().messages().get(
                userId="me",
                id=msg_ref["id"],
                format="full",
            ).execute()

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            body = extract_body(msg["payload"])

            emails.append({
                "id": msg["id"],
                "thread_id": msg["threadId"],
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "date": headers.get("Date", ""),
                "body": body[:3000],
                "label_ids": msg.get("labelIds", []),
                "account": account_email,
            })

            if i % 10 == 0:
                print(f"  {label}Fetched {i}/{len(message_refs)} emails...")

        except Exception as e:
            print(f"  Warning: Could not fetch message {msg_ref['id']}: {e}")

    print(f"Done. Fetched {len(emails)} emails.")
    return emails


if __name__ == "__main__":
    max_emails = int(os.getenv("MAX_EMAILS_TO_FETCH", 50))
    emails = fetch_unread_emails(max_results=max_emails)

    os.makedirs(".tmp", exist_ok=True)
    output_path = ".tmp/fetched_emails.json"
    with open(output_path, "w") as f:
        json.dump(emails, f, indent=2)

    print(f"Saved {len(emails)} emails to {output_path}")
