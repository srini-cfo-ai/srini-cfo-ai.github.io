"""Turn a blog post into a video script + platform-specific social copy."""
from __future__ import annotations

import json
import re

from . import llm
from .content import SOCIAL_DIR, Post

SYSTEM = """You are the social media producer for {name}, {headline}.
Voice: {voice}
You repurpose the author's blog post. Use ONLY facts and claims that appear in the post.
Never invent numbers, clients, employers or results. UK English. No emojis except where noted."""

PROMPT = """Blog post title: {title}
Post URL: {url}

Post:
{body}

Return JSON with exactly these keys:
{{
 "video": {{
   "hook": "spoken opening line, max 20 words, makes a finance leader keep watching",
   "slides": [ {{"heading": "max 8 words", "narration": "2-3 spoken sentences, 35-55 words"}} ],   // 4 to 6 slides
   "close": "spoken closing line inviting viewers to read the full post at the site, max 25 words"
 }},
 "short": {{
   "hook": "spoken hook, max 15 words",
   "slides": [ {{"heading": "max 6 words", "narration": "one spoken sentence, max 22 words"}} ],   // exactly 3 slides
   "close": "max 12 words, e.g. 'Full article — link in bio.'"
 }},
 "linkedin": "LinkedIn post 120-220 words: strong first line, short paragraphs, 3-5 bullet-style insights using the • character, end with a question to drive comments, then 3-5 hashtags. Do not include the URL.",
 "x": "X post, max 230 characters, no URL, 1-2 hashtags",
 "facebook": "Facebook post 60-120 words, conversational, no URL",
 "instagram": "Instagram Reel caption 80-150 words, line breaks, 1-3 emojis allowed, ends with 'Full article: link in bio' and 8-12 hashtags",
 "threads": "Threads post max 450 characters, no URL",
 "bluesky": "Bluesky post max 240 characters, no URL",
 "youtube_title": "max 90 characters, search-friendly",
 "youtube_description": "120-200 words describing the video, ending with 3 hashtags. Do not include the URL.",
 "tags": ["8-12 short keyword tags without #"]
}}"""


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 4]


def fallback_copy(post: Post, profile: dict) -> dict:
    """Deterministic copy if no LLM is reachable: built from the post's own headings and sentences."""
    sections = re.split(r"^##\s+", post.body_md, flags=re.M)
    slides = []
    for sec in sections[1:7]:
        heading, _, rest = sec.partition("\n")
        sents = _sentences(re.sub(r"[*_`#>-]", "", rest))
        if sents:
            heading = re.sub(r"^\d+[.)]\s*", "", heading.strip())[:60]
            slides.append({"heading": heading, "narration": " ".join(sents[:2])})
    if not slides:
        sents = _sentences(post.plain_text)
        slides = [{"heading": f"Point {i + 1}", "narration": s} for i, s in enumerate(sents[:4])]
    tags = [t.replace(" ", "") for t in post.tags] or ["AI", "Finance", "CFO"]
    hashtags = " ".join("#" + t for t in tags[:4])
    return {
        "video": {"hook": post.summary, "slides": slides,
                  "close": "Read the full article on my website."},
        "short": {"hook": post.title, "slides": [{"heading": s["heading"], "narration": _sentences(s["narration"])[0] if _sentences(s["narration"]) else s["narration"]} for s in slides[:3]],
                  "close": "Full article — link in bio."},
        "linkedin": f"{post.title}\n\n{post.summary}\n\n" + "\n".join(f"• {s['heading']}" for s in slides) +
                    f"\n\nWhat would you add?\n\n{hashtags}",
        "x": f"{post.title} {hashtags}"[:230],
        "facebook": f"{post.title}\n\n{post.summary}",
        "instagram": f"{post.title}\n\n{post.summary}\n\nFull article: link in bio\n\n{hashtags} #CFO #FinanceTransformation",
        "threads": f"{post.title}\n\n{post.summary}"[:450],
        "bluesky": f"{post.title} — {post.summary}"[:240],
        "youtube_title": post.title[:90],
        "youtube_description": f"{post.summary}\n\n{hashtags}",
        "tags": tags + ["CFO", "AI in finance", "finance transformation"],
        "_source": "fallback",
    }


def make_copy(post: Post, profile: dict, url: str, force: bool = False) -> dict:
    path = SOCIAL_DIR / f"{post.slug}.json"
    if path.exists() and not force:
        return json.loads(path.read_text(encoding="utf-8"))
    copy = None
    if llm.available():
        try:
            copy = llm.chat_json(
                SYSTEM.format(name=profile["display_name"], headline=profile["headline"], voice=profile.get("voice", "")),
                PROMPT.format(title=post.title, url=url, body=post.body_md[:12000]))
            assert copy["video"]["slides"] and copy["short"]["slides"] and copy["linkedin"]
            copy["_source"] = "llm"
        except Exception as e:
            print(f"[copy] LLM copy failed, using fallback: {e}")
            copy = None
    copy = copy or fallback_copy(post, profile)
    copy["url"] = url
    SOCIAL_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(copy, indent=2, ensure_ascii=False), encoding="utf-8")
    return copy
