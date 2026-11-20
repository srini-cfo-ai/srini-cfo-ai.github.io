"""One-time: get a YouTube refresh token for the publishing workflow.

1. Google Cloud Console -> new project -> enable "YouTube Data API v3".
2. OAuth consent screen: External, add yourself as a Test user, then click "Publish app"
   (otherwise the refresh token expires after 7 days).
3. Credentials -> Create OAuth client ID -> Desktop app -> download JSON as tools/client_secret.json
4. Run:  python tools/get_youtube_token.py
   Sign in with the Google account that owns your YouTube channel.
5. Copy the three printed values into GitHub -> Settings -> Secrets -> Actions.
"""
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

secret = Path(__file__).with_name("client_secret.json")
flow = InstalledAppFlow.from_client_secrets_file(str(secret), ["https://www.googleapis.com/auth/youtube.upload"])
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
cfg = json.loads(secret.read_text())["installed"]
print("\nAdd these as GitHub Actions secrets:\n")
print("YT_CLIENT_ID     =", cfg["client_id"])
print("YT_CLIENT_SECRET =", cfg["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
