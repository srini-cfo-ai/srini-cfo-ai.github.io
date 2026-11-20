"""Load the profile, blog posts and publishing state."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
POSTS_DIR = CONTENT / "posts"
SOCIAL_DIR = CONTENT / "social"
MEDIA_DIR = ROOT / "media"
STATE_FILE = ROOT / "state" / "published.json"

_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)


@dataclass
class Post:
    slug: str
    title: str
    date: dt.date
    summary: str
    tags: list[str]
    body_md: str
    html: str
    path: Path
    draft: bool = False
    social: bool = True
    meta: dict = field(default_factory=dict)

    @property
    def url_path(self) -> str:
        return f"blog/{self.slug}/"

    @property
    def reading_minutes(self) -> int:
        return max(1, round(len(self.body_md.split()) / 220))

    @property
    def plain_text(self) -> str:
        t = re.sub(r"```.*?```", " ", self.body_md, flags=re.S)
        t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
        t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
        t = re.sub(r"[#>*_`|]+", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    @property
    def is_live(self) -> bool:
        return not self.draft and self.date <= today()


def today() -> dt.date:
    override = os.getenv("PORTAL_TODAY")
    return dt.date.fromisoformat(override) if override else dt.date.today()


def site_url(profile: dict | None = None) -> str:
    url = os.getenv("SITE_URL") or (profile or load_profile()).get("site_url") or ""
    return url.rstrip("/")


def load_profile() -> dict:
    return yaml.safe_load((CONTENT / "profile.yml").read_text(encoding="utf-8")) or {}


def parse_post(path: Path) -> Post:
    text = path.read_text(encoding="utf-8")
    m = _FM.match(text)
    meta, body = (yaml.safe_load(m[1]) or {}, m[2]) if m else ({}, text)
    name = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", path.stem)
    date = meta.get("date") or (name[1] if name else today().isoformat())
    if isinstance(date, dt.datetime):
        date = date.date()
    elif isinstance(date, str):
        date = dt.date.fromisoformat(date[:10])
    slug = meta.get("slug") or (name[2] if name else path.stem)
    html = markdown.markdown(body, extensions=["extra", "sane_lists", "smarty"])
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    summary = meta.get("summary") or ""
    post = Post(slug=slug, title=meta.get("title", slug.replace("-", " ").title()),
                date=date, summary=summary, tags=tags, body_md=body, html=html,
                path=path, draft=bool(meta.get("draft", False)),
                social=meta.get("social", True) is not False, meta=meta)
    if not post.summary:
        post.summary = post.plain_text[:200].rsplit(" ", 1)[0] + "…"
    return post


def load_posts(include_unpublished: bool = False) -> list[Post]:
    posts = [parse_post(p) for p in POSTS_DIR.glob("*.md")]
    if not include_unpublished:
        posts = [p for p in posts if p.is_live]
    return sorted(posts, key=lambda p: (p.date, p.slug), reverse=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"posts": {}, "drafted_topics": []}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_social_copy(slug: str) -> dict | None:
    f = SOCIAL_DIR / f"{slug}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
