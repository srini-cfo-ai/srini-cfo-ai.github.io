"""Build the static site into _site/.   Usage:  python -m portal.build"""
from __future__ import annotations

import datetime as dt
import shutil
import time
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import graphics
from .content import MEDIA_DIR, ROOT, load_posts, load_profile, load_state, site_url

OUT = ROOT / "_site"
HERE = Path(__file__).parent

SOCIAL_LABELS = [("linkedin", "LinkedIn"), ("youtube", "YouTube"), ("x", "X"),
                 ("instagram", "Instagram"), ("facebook", "Facebook"), ("threads", "Threads"),
                 ("bluesky", "Bluesky"), ("github", "GitHub")]


def build() -> Path:
    profile = load_profile()
    profile.setdefault("social", {})
    base = site_url(profile)
    posts = load_posts()
    state = load_state()

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(HERE / "static", OUT)
    if MEDIA_DIR.exists():
        shutil.copytree(MEDIA_DIR, OUT / "media", dirs_exist_ok=True)

    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape())
    common = dict(p=profile, site_url=base, social_labels=SOCIAL_LABELS, year=dt.date.today().year,
                  build_id=int(time.time()), has_photo=(OUT / "photo.jpg").exists())

    def render(tpl: str, rel: str, depth: int, **kw):
        path = OUT / rel / "index.html" if rel else OUT / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        html = env.get_template(tpl).render(root="../" * depth, page_path=rel + ("/" if rel else ""), **common, **kw)
        path.write_text(html, encoding="utf-8")

    footer = base.replace("https://", "") or profile["display_name"]
    graphics.render_card(OUT / "og" / "home.png", (1200, 630), kicker=profile["headline"],
                         title=profile["display_name"], body=profile["tagline"].strip(), footer=footer)
    for post in posts:
        graphics.render_card(OUT / "og" / f"{post.slug}.png", (1200, 630), kicker="Insights · " + profile["display_name"],
                             title=post.title, footer=footer)

    render("index.html", "", 0, posts=posts)
    render("blog.html", "blog", 1, posts=posts)
    for post in posts:
        yt = state.get("posts", {}).get(post.slug, {}).get("youtube", {})
        render("post.html", f"blog/{post.slug}", 2, post=post,
               abs_url=f"{base}/{post.url_path}", youtube_id=yt.get("id") if isinstance(yt, dict) else None,
               has_video=(MEDIA_DIR / post.slug / "long.mp4").exists())

    (OUT / "404.html").write_text((OUT / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
    _feeds(profile, posts, base)
    (OUT / ".nojekyll").write_text("")
    print(f"Built {len(posts)} post(s) -> {OUT}")
    return OUT


def _feeds(profile, posts, base):
    items = []
    for p in posts[:30]:
        when = dt.datetime.combine(p.date, dt.time(8, 0), dt.timezone.utc)
        items.append(f"<item><title>{escape(p.title)}</title><link>{base}/{p.url_path}</link>"
                     f"<guid>{base}/{p.url_path}</guid><pubDate>{format_datetime(when)}</pubDate>"
                     f"<description>{escape(p.summary)}</description></item>")
    rss = (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
           f"<title>{escape(profile['display_name'])} — Insights</title><link>{base}/</link>"
           f"<description>{escape(profile['headline'])}</description>{''.join(items)}</channel></rss>")
    (OUT / "feed.xml").write_text(rss, encoding="utf-8")
    urls = [f"{base}/", f"{base}/blog/"] + [f"{base}/{p.url_path}" for p in posts]
    sm = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    sm += "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>"
    (OUT / "sitemap.xml").write_text(sm, encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")


if __name__ == "__main__":
    build()
