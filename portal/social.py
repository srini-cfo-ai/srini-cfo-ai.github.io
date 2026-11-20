"""One function per platform. Each returns a result dict, or None when that platform
is not configured (its secrets are missing) so it is simply skipped."""
from __future__ import annotations

import datetime as dt
import os
import re
import time
from pathlib import Path

import requests

GRAPH = f"https://graph.facebook.com/{os.getenv('META_GRAPH_VERSION', 'v23.0')}"


def env(*names: str) -> list[str] | None:
    vals = [os.getenv(n, "").strip() for n in names]
    return vals if all(vals) else None


def _ok(r: requests.Response) -> dict:
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code} {r.text[:600]}")
    return r.json() if r.text.strip().startswith("{") else {}


# ----------------------------------------------------------------------------- LinkedIn
def _li_escape(text: str) -> str:
    # LinkedIn "little text format" reserves these characters in commentary
    return re.sub(r"([\\|{}@\[\]()<>#*_~])", r"\\\1", text)


def _li_versions():
    if os.getenv("LINKEDIN_VERSION"):
        yield os.getenv("LINKEDIN_VERSION")
    d = dt.date.today().replace(day=1)
    for _ in range(12):
        yield d.strftime("%Y%m")
        d = (d - dt.timedelta(days=1)).replace(day=1)


def linkedin(post, copy, url, media):
    cfg = env("LINKEDIN_ACCESS_TOKEN")
    if not cfg:
        return None
    token = cfg[0]
    author = os.getenv("LINKEDIN_PERSON_URN", "").strip()
    if not author:
        me = _ok(requests.get("https://api.linkedin.com/v2/userinfo", headers={"Authorization": f"Bearer {token}"}, timeout=30))
        author = f"urn:li:person:{me['sub']}"
    body = {
        "author": author, "commentary": _li_escape(copy["linkedin"]), "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
        "content": {"article": {"source": url, "title": post.title[:200], "description": post.summary[:250]}},
        "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False,
    }
    last = None
    for v in _li_versions():
        r = requests.post("https://api.linkedin.com/rest/posts", json=body, timeout=60, headers={
            "Authorization": f"Bearer {token}", "LinkedIn-Version": v,
            "X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json"})
        if r.status_code in (200, 201):
            pid = r.headers.get("x-restli-id", "")
            return {"id": pid, "url": f"https://www.linkedin.com/feed/update/{pid}/"}
        last = f"{r.status_code} {r.text[:400]}"
        if "VERSION" not in r.text.upper():
            break
    raise RuntimeError(last)


# ----------------------------------------------------------------------------- X / Twitter
def x(post, copy, url, media):
    cfg = env("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
    if not cfg:
        return None
    import tweepy
    client = tweepy.Client(consumer_key=cfg[0], consumer_secret=cfg[1], access_token=cfg[2], access_token_secret=cfg[3])
    text = copy["x"][:250].rstrip() + "\n" + url
    res = client.create_tweet(text=text)
    tid = res.data["id"]
    return {"id": tid, "url": f"https://x.com/i/status/{tid}"}


# ----------------------------------------------------------------------------- Facebook Page
def facebook(post, copy, url, media):
    cfg = env("FB_PAGE_ID", "FB_PAGE_TOKEN")
    if not cfg:
        return None
    page, token = cfg
    if media.get("long_url"):
        r = _ok(requests.post(f"{GRAPH}/{page}/videos", timeout=300, data={
            "file_url": media["long_url"], "title": post.title[:250],
            "description": f"{copy['facebook']}\n\nRead more: {url}", "access_token": token}))
        return {"id": r.get("id"), "url": f"https://www.facebook.com/{r.get('id')}"}
    r = _ok(requests.post(f"{GRAPH}/{page}/feed", timeout=60,
                          data={"message": copy["facebook"], "link": url, "access_token": token}))
    return {"id": r.get("id"), "url": f"https://www.facebook.com/{r.get('id')}"}


# ----------------------------------------------------------------------------- Instagram Reels
def instagram(post, copy, url, media):
    cfg = env("IG_USER_ID", "IG_ACCESS_TOKEN")
    if not cfg or not media.get("short_url"):
        return None
    uid, token = cfg
    c = _ok(requests.post(f"{GRAPH}/{uid}/media", timeout=120, data={
        "media_type": "REELS", "video_url": media["short_url"], "caption": copy["instagram"][:2100],
        "share_to_feed": "true", "access_token": token}))
    cid = c["id"]
    for _ in range(60):  # wait up to ~10 min for Instagram to process the video
        s = _ok(requests.get(f"{GRAPH}/{cid}", params={"fields": "status_code,status", "access_token": token}, timeout=30))
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram processing error: {s}")
        time.sleep(10)
    p = _ok(requests.post(f"{GRAPH}/{uid}/media_publish", data={"creation_id": cid, "access_token": token}, timeout=60))
    link = _ok(requests.get(f"{GRAPH}/{p['id']}", params={"fields": "permalink", "access_token": token}, timeout=30))
    return {"id": p["id"], "url": link.get("permalink", "")}


# ----------------------------------------------------------------------------- Threads
def threads(post, copy, url, media):
    cfg = env("THREADS_USER_ID", "THREADS_ACCESS_TOKEN")
    if not cfg:
        return None
    uid, token = cfg
    base = "https://graph.threads.net/v1.0"
    c = _ok(requests.post(f"{base}/{uid}/threads", timeout=60, data={
        "media_type": "TEXT", "text": f"{copy['threads'][:440]}\n\n{url}", "access_token": token}))
    time.sleep(5)
    p = _ok(requests.post(f"{base}/{uid}/threads_publish", data={"creation_id": c["id"], "access_token": token}, timeout=60))
    return {"id": p["id"]}


# ----------------------------------------------------------------------------- Bluesky
def bluesky(post, copy, url, media):
    cfg = env("BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD")
    if not cfg:
        return None
    s = _ok(requests.post("https://bsky.social/xrpc/com.atproto.server.createSession",
                          json={"identifier": cfg[0], "password": cfg[1]}, timeout=30))
    text = copy["bluesky"][:290]
    record = {
        "$type": "app.bsky.feed.post", "text": text,
        "createdAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "embed": {"$type": "app.bsky.embed.external",
                  "external": {"uri": url, "title": post.title[:300], "description": post.summary[:300]}},
    }
    r = _ok(requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord", timeout=30,
                          headers={"Authorization": f"Bearer {s['accessJwt']}"},
                          json={"repo": s["did"], "collection": "app.bsky.feed.post", "record": record}))
    rkey = r["uri"].rsplit("/", 1)[-1]
    return {"id": r["uri"], "url": f"https://bsky.app/profile/{cfg[0]}/post/{rkey}"}


# ----------------------------------------------------------------------------- YouTube
def _youtube_client():
    cfg = env("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
    if not cfg:
        return None
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(None, refresh_token=cfg[2], token_uri="https://oauth2.googleapis.com/token",
                        client_id=cfg[0], client_secret=cfg[1],
                        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def _yt_upload(yt, path: Path, title: str, description: str, tags: list[str]):
    from googleapiclient.http import MediaFileUpload
    body = {
        "snippet": {"title": title[:100], "description": description[:4900], "tags": tags[:15],
                    "categoryId": os.getenv("YT_CATEGORY", "27")},  # 27 = Education
        "status": {"privacyStatus": os.getenv("YT_PRIVACY", "public"), "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(path), chunksize=-1, resumable=True, mimetype="video/mp4"))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


def youtube(post, copy, url, media):
    yt = _youtube_client()
    if not yt or not media.get("long_path"):
        return None
    desc = f"{copy['youtube_description']}\n\nRead the full article: {url}\n\nNarration is AI-generated from the author's own article."
    vid = _yt_upload(yt, media["long_path"], copy["youtube_title"], desc, copy.get("tags", []))
    return {"id": vid, "url": f"https://youtu.be/{vid}"}


def youtube_short(post, copy, url, media):
    yt = _youtube_client()
    if not yt or not media.get("short_path"):
        return None
    title = (copy["youtube_title"][:88] + " #Shorts")
    desc = f"{post.summary}\n\nFull article: {url}\n\n#Shorts #CFO #AIinFinance"
    vid = _yt_upload(yt, media["short_path"], title, desc, copy.get("tags", []))
    return {"id": vid, "url": f"https://youtube.com/shorts/{vid}"}


# Order matters: YouTube first so its link exists before the site is rebuilt.
PLATFORMS = {
    "youtube": youtube, "youtube_short": youtube_short, "linkedin": linkedin, "x": x,
    "facebook": facebook, "instagram": instagram, "threads": threads, "bluesky": bluesky,
}
