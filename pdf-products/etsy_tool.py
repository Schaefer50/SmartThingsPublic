#!/usr/bin/env python3
"""Create Etsy draft listings for the products built in this folder.

Credentials come from the environment, never from this repo:
    ETSY_API_KEY        app keystring
    ETSY_SHARED_SECRET  app shared secret
    ETSY_TOKEN_FILE     where the OAuth token is kept (default ~/.etsy_token.json)
    ETSY_REFRESH_TOKEN  optional; used to log in without the browser step

    python3 etsy_tool.py login                 # print the one-time login link
    python3 etsy_tool.py finish-login '<localhost URL you were sent to>'
    python3 etsy_tool.py whoami
    python3 etsy_tool.py draft listings/planner-blush.json

Drafts are never published by this tool; publish them in Shop Manager.
"""

import base64
import hashlib
import html
import json
import os
import secrets
import sys
import time
import urllib.parse

import requests

API = "https://openapi.etsy.com/v3/application"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
REDIRECT = "http://localhost:3003/oauth/redirect"
SCOPES = "listings_r listings_w shops_r"
HERE = os.path.dirname(os.path.abspath(__file__))


def env(name):
    val = os.environ.get(name)
    if not val:
        sys.exit(f"Set {name} in the environment first.")
    return val


def token_file():
    return os.path.expanduser(os.environ.get("ETSY_TOKEN_FILE", "~/.etsy_token.json"))


def save_token(tok):
    tok["expires_at"] = time.time() + tok["expires_in"] - 60
    path = token_file()
    with open(path, "w") as f:
        json.dump(tok, f)
    os.chmod(path, 0o600)
    return tok


def refresh(refresh_token):
    r = requests.post(TOKEN_URL, data={"grant_type": "refresh_token",
                                      "client_id": env("ETSY_API_KEY"),
                                      "refresh_token": refresh_token})
    r.raise_for_status()
    return save_token(r.json())


def access_token():
    path = token_file()
    if os.path.exists(path):
        tok = json.load(open(path))
        if tok.get("expires_at", 0) > time.time():
            return tok
        return refresh(tok["refresh_token"])
    if os.environ.get("ETSY_REFRESH_TOKEN"):
        return refresh(os.environ["ETSY_REFRESH_TOKEN"])
    sys.exit("Not logged in. Run: etsy_tool.py login")


def headers():
    tok = access_token()
    return {"x-api-key": f"{env('ETSY_API_KEY')}:{env('ETSY_SHARED_SECRET')}",
            "Authorization": f"Bearer {tok['access_token']}"}


def call(method, path, **kw):
    r = requests.request(method, API + path, headers=headers(), **kw)
    if not r.ok:
        sys.exit(f"{method} {path} failed ({r.status_code}): {r.text}")
    return r.json()


def user_id():
    return access_token()["access_token"].split(".")[0]


def shop():
    return call("GET", f"/users/{user_id()}/shops")


# ---------- commands ----------

def cmd_login():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(12)
    with open(token_file() + ".pkce", "w") as f:
        json.dump({"verifier": verifier, "state": state}, f)
    print("https://www.etsy.com/oauth/connect?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": env("ETSY_API_KEY"), "redirect_uri": REDIRECT,
        "scope": SCOPES, "state": state, "code_challenge": challenge,
        "code_challenge_method": "S256"}))


def cmd_finish_login(url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    pkce = json.load(open(token_file() + ".pkce"))
    if q["state"][0] != pkce["state"]:
        sys.exit("State does not match; start again with: etsy_tool.py login")
    r = requests.post(TOKEN_URL, data={"grant_type": "authorization_code",
                                      "client_id": env("ETSY_API_KEY"), "redirect_uri": REDIRECT,
                                      "code": q["code"][0], "code_verifier": pkce["verifier"]})
    r.raise_for_status()
    save_token(r.json())
    os.remove(token_file() + ".pkce")
    cmd_whoami()


def cmd_whoami():
    s = shop()
    print(f"{s['shop_name']} (shop {s['shop_id']}): {s['listing_active_count']} active listings")


def cmd_draft(spec_path):
    """Create a draft listing from a JSON spec, then attach its photos and files."""
    spec = json.load(open(spec_path))
    base = os.path.dirname(os.path.abspath(spec_path))
    resolve = lambda p: os.path.normpath(os.path.join(base, p))
    shop_id = shop()["shop_id"]
    fields = {k: v for k, v in spec.items() if k not in ("images", "files")}
    fields["description"] = html.unescape(fields["description"])
    listing = call("POST", f"/shops/{shop_id}/listings", data=fields)
    lid = listing["listing_id"]
    print(f"draft {lid}: {listing['title']}")
    for rank, img in enumerate(spec["images"], start=1):
        with open(resolve(img), "rb") as f:
            call("POST", f"/shops/{shop_id}/listings/{lid}/images",
                 files={"image": (os.path.basename(img), f, "image/jpeg")}, data={"rank": rank})
        print(f"  photo {rank}: {os.path.basename(img)}")
    for rank, pdf in enumerate(spec["files"], start=1):
        with open(resolve(pdf), "rb") as f:
            call("POST", f"/shops/{shop_id}/listings/{lid}/files",
                 files={"file": (os.path.basename(pdf), f, "application/pdf")},
                 data={"name": os.path.basename(pdf), "rank": rank})
        print(f"  file {rank}: {os.path.basename(pdf)}")
    print(f"  review: https://www.etsy.com/your/shops/me/listing-editor/edit/{lid}")
    return lid


if __name__ == "__main__":
    cmds = {"login": cmd_login, "finish-login": cmd_finish_login,
            "whoami": cmd_whoami, "draft": cmd_draft}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](*sys.argv[2:])
