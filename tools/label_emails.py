import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.gmail_auth import get_gmail_service

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, ".env"))


def get_or_create_label(service, label_name):
    """Return the ID of the label, creating it if it doesn't exist."""
    existing = service.users().labels().list(userId="me").execute()

    for label in existing.get("labels", []):
        if label["name"].lower() == label_name.lower():
            print(f"Found existing label '{label_name}' (ID: {label['id']})")
            return label["id"]

    new_label = service.users().labels().create(
        userId="me",
        body={
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()

    print(f"Created new label '{label_name}' (ID: {new_label['id']})")
    return new_label["id"]


def apply_label_and_archive(service, email_id, label_id):
    """Apply the school label and remove INBOX label (archives from inbox)."""
    service.users().messages().modify(
        userId="me",
        id=email_id,
        body={
            "addLabelIds": [label_id],
            "removeLabelIds": ["INBOX"],
        },
    ).execute()


def _apply_label_batch(service, emails, label_id, label_name, account_label):
    """Apply a label to a list of emails and archive them. Returns (labeled_ids, errors)."""
    labeled = []
    errors = []
    for i, email in enumerate(emails, 1):
        try:
            apply_label_and_archive(service, email["id"], label_id)
            labeled.append(email["id"])
            print(f"  [{i}/{len(emails)}] [{label_name}] Labeled + archived: {email['subject'][:55]}")
        except Exception as e:
            errors.append({"email_id": email["id"], "subject": email["subject"], "error": str(e)})
            print(f"  [{i}/{len(emails)}] [{label_name}] Failed: {email['subject'][:55]} — {e}")
    return labeled, errors


def label_school_emails(college_emails, school_emails, account_email=None):
    """Apply 'college' and 'school' labels to the respective email lists and archive them.

    account_email: if provided, authenticates as that specific account.
    Returns (labeled_ids, errors) lists covering both label groups.
    """
    if not college_emails and not school_emails:
        print("No college or school emails to label.")
        return [], []

    college_label_name = os.getenv("COLLEGE_LABEL_NAME", "college")
    school_label_name = os.getenv("SCHOOL_LABEL_NAME", "school")
    service = get_gmail_service(account_email=account_email)
    account_label = f"[{account_email}] " if account_email else ""

    all_labeled = []
    all_errors = []

    if college_emails:
        college_label_id = get_or_create_label(service, college_label_name)
        print(f"{account_label}Applying '{college_label_name}' label to {len(college_emails)} emails...")
        labeled, errors = _apply_label_batch(service, college_emails, college_label_id, college_label_name, account_label)
        all_labeled.extend(labeled)
        all_errors.extend(errors)

    if school_emails:
        school_label_id = get_or_create_label(service, school_label_name)
        print(f"{account_label}Applying '{school_label_name}' label to {len(school_emails)} emails...")
        labeled, errors = _apply_label_batch(service, school_emails, school_label_id, school_label_name, account_label)
        all_labeled.extend(labeled)
        all_errors.extend(errors)

    print(f"\nTotal labeled: {len(all_labeled)}, Errors: {len(all_errors)}")
    return all_labeled, all_errors


if __name__ == "__main__":
    input_path = os.path.join(_project_root, ".tmp/classified_emails.json")
    if not os.path.exists(input_path):
        print("No classified_emails.json found. Run classify_emails.py first.")
    else:
        with open(input_path) as f:
            data = json.load(f)
        label_school_emails(data.get("college_emails", []), data.get("school_emails", []))
