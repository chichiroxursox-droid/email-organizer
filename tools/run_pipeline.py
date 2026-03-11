import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, ".env"))

sys.path.insert(0, _project_root)

MIN_RUN_INTERVAL_HOURS = 3
_last_run_path = os.path.join(_project_root, ".tmp", "last_run.txt")


def _check_cooldown():
    """Return (should_skip, reason_string). Skips if last run was too recent."""
    if not os.path.exists(_last_run_path):
        return False, None
    try:
        with open(_last_run_path) as f:
            last_run = datetime.fromisoformat(f.read().strip())
        elapsed_hours = (datetime.now(timezone.utc) - last_run).total_seconds() / 3600
        if elapsed_hours < MIN_RUN_INTERVAL_HOURS:
            mins = int(elapsed_hours * 60)
            return True, f"Last run was {mins} minutes ago (cooldown: {MIN_RUN_INTERVAL_HOURS}h). Skipping."
    except Exception:
        pass
    return False, None


def _record_last_run():
    """Write current UTC timestamp to last_run.txt."""
    os.makedirs(os.path.dirname(_last_run_path), exist_ok=True)
    with open(_last_run_path, "w") as f:
        f.write(datetime.now(timezone.utc).isoformat())


def run_for_account(account_email=None):
    """Run the full pipeline for a single Gmail account."""
    label = f"[{account_email}]" if account_email else "[default]"

    print(f"\n{'=' * 50}")
    print(f"  Processing account: {account_email or 'default'}")
    print(f"{'=' * 50}")

    # Step 1: Fetch emails
    print(f"\n{label} Step 1/4: Fetching unread emails...")
    try:
        from tools.fetch_emails import fetch_unread_emails
        max_emails = int(os.getenv("MAX_EMAILS_TO_FETCH", 50))
        emails = fetch_unread_emails(max_results=max_emails, account_email=account_email)
        print(f"{label} → {len(emails)} emails fetched.")
    except Exception as e:
        print(f"{label} FATAL: Could not fetch emails: {e}")
        return {"account": account_email, "error": str(e)}

    if not emails:
        print(f"{label} No unread emails. Skipping.")
        return {"account": account_email, "fetched": 0, "school": 0, "drafts": 0, "labeled": 0}

    # Step 2: Classify with Claude
    print(f"\n{label} Step 2/4: Classifying emails with Claude AI...")
    try:
        from tools.classify_emails import classify_emails
        result = classify_emails(emails)
        college_emails = result["college_emails"]
        school_emails = result["school_emails"]
        school_count = len(college_emails) + len(school_emails)
        print(f"{label} → {len(college_emails)} college, {len(school_emails)} school emails found.")
    except Exception as e:
        print(f"{label} FATAL: Classification failed: {e}")
        return {"account": account_email, "error": str(e)}

    if school_count == 0:
        print(f"{label} No school or college emails found. Nothing to label or draft.")
        return {"account": account_email, "fetched": len(emails), "college": 0, "school": 0, "drafts": 0, "labeled": 0}

    # Step 3: Create drafts (for all school-related emails)
    all_school_emails = college_emails + school_emails
    print(f"\n{label} Step 3/4: Creating draft replies...")
    try:
        from tools.create_drafts import create_all_drafts
        drafts, draft_errors = create_all_drafts(all_school_emails, account_email=account_email)
        print(f"{label} → {len(drafts)} drafts created.")
    except Exception as e:
        print(f"{label} WARNING: Draft creation failed: {e}")
        drafts, draft_errors = [], [str(e)]

    # Step 4: Label and archive
    print(f"\n{label} Step 4/4: Applying 'college' and 'school' labels...")
    try:
        from tools.label_emails import label_school_emails
        labeled, label_errors = label_school_emails(college_emails, school_emails, account_email=account_email)
        print(f"{label} → {len(labeled)} emails labeled and archived.")
    except Exception as e:
        print(f"{label} FATAL: Labeling failed: {e}")
        return {"account": account_email, "error": str(e)}

    return {
        "account": account_email,
        "fetched": len(emails),
        "college": len(college_emails),
        "school": len(school_emails),
        "drafts": len(drafts),
        "labeled": len(labeled),
    }


def run_pipeline():
    print("=" * 50)
    print("  Gmail School Email Organizer")
    print("=" * 50)

    # Skip if run too recently (launchd fires every hour, we only want to run every 3h)
    should_skip, reason = _check_cooldown()
    if should_skip:
        print(f"\n{reason}")
        return

    # Support multiple accounts via comma-separated GMAIL_ACCOUNTS env var
    accounts_env = os.getenv("GMAIL_ACCOUNTS", "").strip()
    if accounts_env:
        accounts = [a.strip() for a in accounts_env.split(",") if a.strip()]
    else:
        accounts = [None]  # None = use default token.json (single account mode)

    results = []
    for account in accounts:
        result = run_for_account(account_email=account)
        results.append(result)

    # Final summary across all accounts
    print(f"\n{'=' * 50}")
    print("  Pipeline Complete — Summary")
    print(f"{'=' * 50}")
    for r in results:
        if "error" in r:
            print(f"  {r['account'] or 'default'}: ERROR — {r['error']}")
        else:
            print(f"  {r['account'] or 'default'}:")
            print(f"    Fetched: {r['fetched']}  |  College: {r.get('college', 0)}  |  School: {r.get('school', 0)}  |  Drafts: {r['drafts']}  |  Labeled: {r['labeled']}")
    print()

    _record_last_run()


if __name__ == "__main__":
    run_pipeline()
