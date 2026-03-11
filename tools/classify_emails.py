import json
import os
import sys

import anthropic
from dotenv import load_dotenv

# Explicitly load .env from the project root regardless of working directory
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, ".env"))

SYSTEM_PROMPT = """You are an email classifier. Your job is to categorize emails into one of three categories: "college", "school", or "other".

Category "college" — email is from or about a college or university (higher education):
- Sender domain is a college or university (.edu domains for higher ed, community colleges, universities)
- Sender is a college-level service: Canvas, Blackboard, Brightspace, Coursera, edX, or similar used at a college/university
- Subject or body mentions: professor, GPA, semester, quarter, tuition, financial aid, FAFSA, student loans, college, university, campus, enrollment, transcript, undergraduate, graduate, dean, major, minor, elective, lecture hall, dormitory, sorority, fraternity
- Email is from college admissions, registrar, bursar, financial aid office, or college student organization

Category "school" — email is from or about a K-12 school (not a college or university):
- Sender domain belongs to a K-12 school or school district (k12.us, school district domains)
- Sender is a K-12 service: PowerSchool, Schoology, ParentSquare, Remind, Google Classroom (K-12 context), ClassDojo
- Subject or body mentions: homework, homeroom, grade (in K-12 context), teacher, principal, parent-teacher, report card, IEP, high school, middle school, elementary school, student ID, school bus
- Email is from a K-12 school club, sports team, or student organization

Category "other" — everything else:
- General marketing or promotions unrelated to education
- Personal correspondence with no academic content
- Work emails, bills, newsletters unrelated to school

When the context is ambiguous, prefer "college" if there are any college-level signals, and "school" if there are K-12 signals.

Respond ONLY with valid JSON in this exact format, with no additional text, no markdown, no code blocks:
{"category": "college", "confidence": "high", "reason": "brief explanation"}

Values for category: "college", "school", or "other"
Confidence levels: "high" (clearly fits the category), "medium" (likely fits), "low" (uncertain)"""


def classify_single_email(client, email, model):
    """Send a single email to Claude for classification. Returns a classification dict."""
    user_message = f"""Classify this email:

FROM: {email['from']}
SUBJECT: {email['subject']}
DATE: {email['date']}
BODY (first 2000 chars):
{email['body'][:2000]}"""

    response = client.messages.create(
        model=model,
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    result_text = response.content[0].text.strip()
    return json.loads(result_text)


def classify_emails(emails=None):
    """Classify emails as school-related or not.

    emails: list of email dicts (from fetch_unread_emails). If not provided,
            falls back to reading from .tmp/fetched_emails.json.
    Returns a dict with school_emails, other_emails, errors, summary.
    """
    if emails is None:
        input_path = os.path.join(_project_root, ".tmp/fetched_emails.json")
        if not os.path.exists(input_path):
            raise FileNotFoundError(
                f"{input_path} not found. Run tools/fetch_emails.py first."
            )
        with open(input_path, "r") as f:
            emails = json.load(f)

    if not emails:
        print("No emails to classify.")
        return {"school_emails": [], "other_emails": [], "errors": [], "summary": {"total": 0, "school": 0, "other": 0, "errors": 0}}

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "sk-ant-your-key-here":
        raise ValueError("ANTHROPIC_API_KEY not set in .env file.")

    model = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")
    client = anthropic.Anthropic(api_key=api_key)

    print(f"Classifying {len(emails)} emails with {model}...")

    college_emails = []
    school_emails = []
    other_emails = []
    errors = []

    for i, email in enumerate(emails, 1):
        try:
            classification = classify_single_email(client, email, model)
            email["classification"] = classification

            category = classification.get("category", "other")
            confidence = classification.get("confidence", "?")

            if category == "college":
                college_emails.append(email)
                label = "COLLEGE"
            elif category == "school":
                school_emails.append(email)
                label = "SCHOOL"
            else:
                other_emails.append(email)
                label = "other"

            print(f"  [{i}/{len(emails)}] {label} ({confidence}): {email['subject'][:50]}")

        except json.JSONDecodeError as e:
            print(f"  [{i}/{len(emails)}] ERROR (bad JSON from Claude): {email['subject'][:50]}")
            errors.append({"email_id": email["id"], "subject": email["subject"], "error": f"JSON parse error: {e}"})
        except Exception as e:
            print(f"  [{i}/{len(emails)}] ERROR: {email['subject'][:50]} — {e}")
            errors.append({"email_id": email["id"], "subject": email["subject"], "error": str(e)})

    output = {
        "college_emails": college_emails,
        "school_emails": school_emails,
        "other_emails": other_emails,
        "errors": errors,
        "summary": {
            "total": len(emails),
            "college": len(college_emails),
            "school": len(school_emails),
            "other": len(other_emails),
            "errors": len(errors),
        },
    }

    os.makedirs(".tmp", exist_ok=True)
    output_path = ".tmp/classified_emails.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nClassification complete:")
    print(f"  College: {len(college_emails)}")
    print(f"  School:  {len(school_emails)}")
    print(f"  Other:   {len(other_emails)}")
    print(f"  Errors:  {len(errors)}")
    print(f"  Saved to {output_path}")

    return output


if __name__ == "__main__":
    classify_emails()
