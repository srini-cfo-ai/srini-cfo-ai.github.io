"""Orchestrates the cross-posting pipeline.

  python -m portal.publish prepare   # AI copy + videos for new posts (before the site is built)
  python -m portal.publish post      # push to every configured platform (after the site is live)
  python -m portal.publish status    # show what has been posted where

Env: SITE_URL, BACKFILL_DAYS (default 21), DRY_RUN=1, ONLY=slug
"""
from __future__ import annotations

import datetime as dt
import os
import sys
import time
import traceback

import requests

from . import copywriter, social, video
from .content import MEDIA_DIR, load_posts, load_profile, load_state, save_state, site_url, today

MAX_ATTEMPTS = 3


def eligible_posts():
    days = int(os.getenv("BACKFILL_DAYS", "21"))
    only = os.getenv("ONLY")
    out = []
    for p in reversed(load_posts()):  # oldest first
        if only and p.slug != only:
            continue
        if p.social and (only or p.date >= today() - dt.timedelta(days=days)):
            out.append(p)
    return out


def prepare():
    profile, state, base = load_profile(), load_state(), site_url()
    for post in eligible_posts():
        url = f"{base}/{post.url_path}"
        rec = state["posts"].setdefault(post.slug, {})
        copy = copywriter.make_copy(post, profile, url)
        if all((MEDIA_DIR / post.slug / f).exists() for f in ("long.mp4", "short.mp4")):
            continue
        print(f"[prepare] {post.slug}: generating videos")
        try:
            video.make_post_videos(post.slug, copy, post.title, profile, url)
            rec["videos"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        except Exception:
            traceback.print_exc()
            rec["video_error"] = traceback.format_exc(limit=2)[-500:]
    save_state(state)


def _wait_public(urls: list[str], timeout=300):
    end = time.time() + timeout
    for u in urls:
        while time.time() < end:
            try:
                if requests.head(u, allow_redirects=True, timeout=20).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(10)


def post_all():
    profile, state, base = load_profile(), load_state(), site_url()
    dry = os.getenv("DRY_RUN") == "1"
    failures = 0
    for post in eligible_posts():
        url = f"{base}/{post.url_path}"
        copy = copywriter.make_copy(post, profile, url)
        rec = state["posts"].setdefault(post.slug, {})
        d = MEDIA_DIR / post.slug
        media = {}
        if (d / "long.mp4").exists():
            media.update(long_path=d / "long.mp4", long_url=f"{base}/media/{post.slug}/long.mp4")
        if (d / "short.mp4").exists():
            media.update(short_path=d / "short.mp4", short_url=f"{base}/media/{post.slug}/short.mp4")
        if media and base and not dry:
            _wait_public([media.get("long_url"), media.get("short_url")])
        for name, fn in social.PLATFORMS.items():
            done = rec.get(name)
            if isinstance(done, dict) and done.get("id"):
                continue
            attempts = rec.setdefault("attempts", {}).get(name, 0)
            if attempts >= MAX_ATTEMPTS:
                continue
            if dry:
                print(f"[dry-run] would post {post.slug} -> {name}")
                continue
            try:
                res = fn(post, copy, url, media)
                if res is None:
                    print(f"[skip] {name}: not configured")
                    continue
                res["at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
                rec[name] = res
                rec.get("errors", {}).pop(name, None)
                print(f"[ok] {post.slug} -> {name} {res.get('url', '')}")
            except Exception as e:
                failures += 1
                rec["attempts"][name] = attempts + 1
                rec.setdefault("errors", {})[name] = str(e)[:500]
                print(f"[fail] {post.slug} -> {name}: {e}")
            save_state(state)
    save_state(state)
    if failures:
        print(f"{failures} platform post(s) failed; they will be retried on the next run (max {MAX_ATTEMPTS}).")


def status():
    state = load_state()
    for slug, rec in state["posts"].items():
        print(slug)
        for name in social.PLATFORMS:
            v = rec.get(name)
            err = rec.get("errors", {}).get(name)
            print(f"  {name:14} {'✔ ' + v.get('url', v.get('id', '')) if isinstance(v, dict) else ('✖ ' + err if err else '—')}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"prepare": prepare, "post": post_all, "status": status}[cmd]()
