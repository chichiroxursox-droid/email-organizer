import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.labels",
]

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_project_root, ".env"))


def get_gmail_service(account_email=None):
    """Authenticate and return an authorized Gmail API service object.

    If account_email is provided, uses a per-account token file (e.g. token_user@gmail.com.json).
    On first run for an account, opens a browser window for OAuth consent.
    Subsequent runs use the cached token file.
    """
    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    # Resolve relative paths from the project root
    if not os.path.isabs(creds_path):
        creds_path = os.path.join(_project_root, creds_path)

    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"credentials.json not found at '{creds_path}'.\n"
            "Download it from Google Cloud Console:\n"
            "  APIs & Services → Credentials → OAuth 2.0 Client ID (Desktop app) → Download JSON\n"
            "Rename the file to 'credentials.json' and place it in the project root."
        )

    # Use a per-account token file if an email is specified
    if account_email:
        token_filename = f"token_{account_email}.json"
    else:
        token_filename = os.getenv("GMAIL_TOKEN_PATH", "token.json")

    token_path = os.path.join(_project_root, token_filename)

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
        print(f"Auth token saved to {token_path}")

    return build("gmail", "v1", credentials=creds)
