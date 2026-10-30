#!/usr/bin/env python
"""One-shot OAuth: open browser, print refresh_token for .env."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parent.parent
SECRET_PATH = ROOT / "client_secret.json"
TOKEN_OUT = ROOT / "token.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main() -> None:
    if not SECRET_PATH.is_file():
        print(f"Missing {SECRET_PATH.name} in project root.", file=sys.stderr)
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(SECRET_PATH), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        print(
            "No refresh_token returned. Revoke app access at "
            "https://myaccount.google.com/permissions and run again.",
            file=sys.stderr,
        )
        sys.exit(1)

    payload = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or SCOPES),
    }
    TOKEN_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    secret = json.loads(SECRET_PATH.read_text(encoding="utf-8"))
    installed = secret.get("installed") or secret.get("web") or {}

    print()
    print("OK. Add to .env:")
    print(f"GOOGLE_CLIENT_ID={installed.get('client_id') or creds.client_id}")
    print(f"GOOGLE_CLIENT_SECRET={installed.get('client_secret') or creds.client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print("GOOGLE_DRIVE_FOLDER_ID=<folder id from Drive URL>")
    print()
    print(f"Also saved: {TOKEN_OUT.name} (gitignored)")


if __name__ == "__main__":
    main()
