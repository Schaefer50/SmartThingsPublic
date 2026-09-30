#!/usr/bin/env python3
"""Post the pins from output/pins/pinterest-bulk-upload.csv to Pinterest.

Credentials come from the environment, never from this repo:
    PINTEREST_APP_ID       app id
    PINTEREST_APP_SECRET   app secret
    PINTEREST_TOKEN_FILE   where the OAuth token is kept (default ~/.pinterest_token.json)
    PINTEREST_SANDBOX=1    use the sandbox API (required while the app has Trial access)

    python3 pinterest_tool.py login
    python3 pinterest_tool.py finish-login '<localhost URL you were sent to>'
    python3 pinterest_tool.py whoami
    python3 pinterest_tool.py post [output/pins/pinterest-bulk-upload.csv]
"""

import base64
import csv
import json
import os
import secrets
import sys
import time
import urllib.parse

import requests

REDIRECT = "http://localhost:3003/oauth/redirect"
SCOPES = "boards:read,boards:write,pins:read,pins:write,user_accounts:read"
HERE = os.path.dirname(os.path.abspath(__file__))


def api():
    host = "api-sandbox.pinterest.com" if os.environ.get("PINTEREST_SANDBOX") else "api.pinterest.com"
    return f"https://{host}/v5"


def env(name):
    val = os.environ.get(name)
    if not val:
        sys.exit(f"Set {name} in the environment first.")
    return val


def token_file():
    return os.path.expanduser(os.environ.get("PINTEREST_TOKEN_FILE", "~/.pinterest_token.json"))


def token_request(data):
    basic = base64.b64encode(f"{env('PINTEREST_APP_ID')}:{env('PINTEREST_APP_SECRET')}".encode()).decode()
    r = requests.post("https://api.pinterest.com/v5/oauth/token", data=data,
                      headers={"Authorization": f"Basic {basic}"})
    if not r.ok:
        sys.exit(f"Token request failed ({r.status_code}): {r.text}")
    tok = r.json()
    tok["expires_at"] = time.time() + tok["expires_in"] - 60
    old = json.load(open(token_file())) if os.path.exists(token_file()) else {}
    tok.setdefault("refresh_token", old.get("refresh_token"))
    with open(token_file(), "w") as f:
        json.dump(tok, f)
    os.chmod(token_file(), 0o600)
    return tok


def access_token():
    if not os.path.exists(token_file()):
        sys.exit("Not logged in. Run: pinterest_tool.py login")
    tok = json.load(open(token_file()))
    if tok["expires_at"] > time.time():
        return tok["access_token"]
    return token_request({"grant_type": "refresh_token",
                          "refresh_token": tok["refresh_token"]})["access_token"]


def call(method, path, **kw):
    r = requests.request(method, api() + path, headers={"Authorization": f"Bearer {access_token()}"}, **kw)
    if not r.ok:
        sys.exit(f"{method} {path} failed ({r.status_code}): {r.text}")
    return r.json() if r.text else {}


def cmd_login():
    state = secrets.token_urlsafe(12)
    with open(token_file() + ".state", "w") as f:
        f.write(state)
    print("https://www.pinterest.com/oauth/?" + urllib.parse.urlencode({
        "client_id": env("PINTEREST_APP_ID"), "redirect_uri": REDIRECT,
        "response_type": "code", "scope": SCOPES, "state": state}))


def cmd_finish_login(url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if q["state"][0] != open(token_file() + ".state").read():
        sys.exit("State does not match; start again with: pinterest_tool.py login")
    token_request({"grant_type": "authorization_code", "code": q["code"][0], "redirect_uri": REDIRECT})
    os.remove(token_file() + ".state")
    cmd_whoami()


def cmd_whoami():
    me = call("GET", "/user_account")
    print(f"{me.get('username')} ({me.get('account_type')}) via {api()}")


def boards():
    found, bookmark = {}, None
    while True:
        page = call("GET", "/boards", params={"page_size": 100, **({"bookmark": bookmark} if bookmark else {})})
        found.update({b["name"]: b["id"] for b in page["items"]})
        bookmark = page.get("bookmark")
        if not bookmark:
            return found


def cmd_post(csv_path=os.path.join(HERE, "output", "pins", "pinterest-bulk-upload.csv")):
    """Create each pin in the CSV, making any missing boards first."""
    existing = boards()
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    for row in rows:
        board = row["Pinterest board"]
        if board not in existing:
            existing[board] = call("POST", "/boards", json={"name": board, "privacy": "PUBLIC"})["id"]
            print(f"created board: {board}")
        pin = call("POST", "/pins", json={
            "board_id": existing[board], "title": row["Title"], "description": row["Description"],
            "link": row["Link"], "alt_text": row["Title"],
            "media_source": {"source_type": "image_url", "url": row["Media URL"]}})
        print(f"pin {pin['id']}: {row['Title']} -> {board}")


if __name__ == "__main__":
    cmds = {"login": cmd_login, "finish-login": cmd_finish_login, "whoami": cmd_whoami, "post": cmd_post}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](*sys.argv[2:])
