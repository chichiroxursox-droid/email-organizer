import base64
import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.gmail_auth import get_gmail_service

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, ".env"))

SCHOOL_KEYWORDS = [
    "teacher", "principal", "school", "counselor", "coach",
    "administrator", "guidance", "homeroom", "homework", "assignment",
    "grade", "class", "classroom", "attendance", "parent", "pta",
    "iep", "tutor", "dean", "superintendent", "professor", "advisor",
    "registrar", "campus", "university", "college", "semester", "course",
    "syllabus", "transcript", "gpa", "fafsa", "financial aid",
]


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


def is_school_related(email):
    """Check if a sent email is school-related based on keywords."""
    text = " ".join([
        email.get("subject", ""),
        email.get("body", ""),
        email.get("to", ""),
    ]).lower()
    return any(kw in text for kw in SCHOOL_KEYWORDS)


def fetch_sent_emails(max_results=100, account_email=None):
    """Fetch sent emails from Gmail SENT folder."""
    service = get_gmail_service(account_email=account_email)

    print(f"Fetching up to {max_results} sent emails...")
    results = service.users().messages().list(
        userId="me",
        labelIds=["SENT"],
        maxResults=max_results,
    ).execute()

    message_refs = results.get("messages", [])
    if not message_refs:
        print("No sent messages found.")
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
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "date": headers.get("Date", ""),
                "body": body[:3000],
                "source": "gmail_sent",
            })

            if i % 20 == 0:
                print(f"  Fetched {i}/{len(message_refs)}...")

        except Exception as e:
            print(f"  Warning: Could not fetch message {msg_ref['id']}: {e}")

    print(f"Fetched {len(emails)} sent emails total.")
    return emails


def load_manual_samples():
    """Load manually written email samples from data/manual_samples.txt."""
    manual_path = os.path.join(_project_root, "data", "manual_samples.txt")
    if not os.path.exists(manual_path):
        return []

    with open(manual_path) as f:
        content = f.read()

    raw_sections = [s.strip() for s in content.split("---") if s.strip()]

    manual = []
    idx = 0
    for section in raw_sections:
        # Skip the instructions header block
        upper = section.upper()
        if "INSTRUCTIONS" in upper or "ADD YOUR EMAILS" in upper or "PASTE EMAILS" in upper:
            continue
        # Skip placeholder sections
        if "(paste your" in section.lower():
            continue
        idx += 1
        manual.append({
            "id": f"manual_{idx}",
            "from": "me",
            "to": "",
            "subject": f"Manual sample {idx}",
            "date": "",
            "body": section,
            "source": "manual",
        })

    return manual


def collect_writing_samples(max_results=100, account_email=None):
    """Fetch sent school-related emails and merge with manual samples.

    Saves results to data/writing_samples.json.
    Returns list of email sample dicts.
    """
    sent = fetch_sent_emails(max_results=max_results, account_email=account_email)

    school_sent = [e for e in sent if is_school_related(e)]
    print(f"Filtered to {len(school_sent)} school-related sent emails.")

    manual = load_manual_samples()
    if manual:
        print(f"Loaded {len(manual)} manual sample(s) from data/manual_samples.txt.")

    all_samples = school_sent + manual

    os.makedirs(os.path.join(_project_root, "data"), exist_ok=True)
    output_path = os.path.join(_project_root, "data", "writing_samples.json")
    with open(output_path, "w") as f:
        json.dump(all_samples, f, indent=2)

    print(f"Saved {len(all_samples)} total writing samples to data/writing_samples.json")
    return all_samples


if __name__ == "__main__":
    account_email = os.getenv("GMAIL_ACCOUNTS", "").split(",")[0].strip() or None
    collect_writing_samples(max_results=100, account_email=account_email)
