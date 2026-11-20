"""One-time (repeat every ~60 days): get a LinkedIn access token that can post as you.

1. https://www.linkedin.com/developers/apps -> Create app (needs a LinkedIn Page; you can
   create a free page for your personal brand). In Products, add
   "Share on LinkedIn" and "Sign In with LinkedIn using OpenID Connect".
2. Auth tab -> Authorized redirect URL: http://localhost:8765/callback
3. Run:  python tools/get_linkedin_token.py <client_id> <client_secret>
4. Copy the printed LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN into GitHub secrets.
"""
import http.server
import secrets
import sys
import urllib.parse
import webbrowser

import requests

import subprocess

cid = sys.argv[1] if len(sys.argv) > 1 else input("LinkedIn app Client ID: ").strip()
if len(sys.argv) > 2:
    csec = sys.argv[2]
else:
    input("Copy the Client Secret (LinkedIn app > Auth > Primary Client Secret > Copy), then press Enter here...")
    csec = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                          capture_output=True, text=True).stdout.strip()
    print(f"Read a {len(csec)}-character secret from the clipboard.")
redirect = "http://localhost:8765/callback"
state = secrets.token_urlsafe(16)
url = "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode({
    "response_type": "code", "client_id": cid, "redirect_uri": redirect, "state": state,
    "scope": "openid profile w_member_social"})
code = {}


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if q.get("state", [""])[0] == state:
            code["v"] = q.get("code", [""])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Done - you can close this tab.")

    def log_message(self, *a):
        pass


print("Opening LinkedIn sign-in in your browser. If nothing opens, open this link:\n" + url)
webbrowser.open(url)
srv = http.server.HTTPServer(("localhost", 8765), H)
while "v" not in code:
    srv.handle_request()
tok = requests.post("https://www.linkedin.com/oauth/v2/accessToken", data={
    "grant_type": "authorization_code", "code": code["v"], "redirect_uri": redirect,
    "client_id": cid, "client_secret": csec}, timeout=30).json()
if "access_token" not in tok:
    sys.exit(f"\nLinkedIn refused the token exchange: {tok.get('error')}: {tok.get('error_description')}\n"
             "Usually this means the Client Secret was wrong. Copy it again and rerun.")
me = requests.get("https://api.linkedin.com/v2/userinfo",
                  headers={"Authorization": f"Bearer {tok['access_token']}"}, timeout=30).json()
print(f"\nSigned in as {me.get('name')}. Token valid for {tok.get('expires_in', 0) // 86400} days.")


def to_clipboard(value: str):
    subprocess.run(["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"], input=value, text=True)


GH = "https://github.com/srini-cfo-ai/srini-cfo-ai.github.io/settings/secrets/actions"
to_clipboard(tok["access_token"])
input(f"\n1) The ACCESS TOKEN is now on your clipboard.\n   On {GH}\n"
      "   click the pencil next to LINKEDIN_ACCESS_TOKEN, paste (Ctrl+V) into the value box, click Update secret.\n"
      "   Then press Enter here...")
to_clipboard(f"urn:li:person:{me['sub']}")
input("\n2) The PERSON URN is now on your clipboard.\n"
      "   Click the pencil next to LINKEDIN_PERSON_URN, paste, click Update secret. Then press Enter here...")
to_clipboard("")
print("\nDone. Clipboard cleared. Rerun this script in about 55 days to renew the token.")
