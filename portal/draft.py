"""AI ghost-writer: drafts a new blog post from the topic list in content/topics.yml.

  python -m portal.draft            # next unused topic
  python -m portal.draft "topic"    # specific topic
Prints the path of the new post file.
"""
from __future__ import annotations

import re
import sys

import yaml

from . import llm
from .content import CONTENT, POSTS_DIR, load_posts, load_profile, load_state, save_state, today

SYSTEM = """You are ghost-writing a blog post for {name}, {headline}.
About the author: {about}
Voice: {voice}
Rules: write as the author in the first person. Use only general, verifiable knowledge and practical
experience framed generically ("in finance teams I have worked with"). Never invent statistics,
survey figures, client names, employers, or quotes. No hype words like 'revolutionise' or 'game-changer'."""

PROMPT = """Write a blog post on: {topic}

Avoid repeating these existing titles: {existing}

Return JSON: {{"title": "...", "summary": "one or two sentences, max 220 characters",
"tags": ["3-4 tags"], "body": "markdown body, 650-900 words, 3-5 '## ' sections, short paragraphs,
at least one bullet list, ending with a practical 'Where to start' section"}}"""


def next_topic(state) -> str:
    topics = yaml.safe_load((CONTENT / "topics.yml").read_text(encoding="utf-8"))["topics"]
    used = set(state.get("drafted_topics", []))
    for t in topics:
        if t not in used:
            return t
    return topics[len(used) % len(topics)]


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:70].rstrip("-")


def draft(topic: str | None = None) -> str:
    profile, state = load_profile(), load_state()
    topic = topic or next_topic(state)
    existing = "; ".join(p.title for p in load_posts(include_unpublished=True))
    data = llm.chat_json(
        SYSTEM.format(name=profile["display_name"], headline=profile["headline"],
                      about=profile.get("about", ""), voice=profile.get("voice", "")),
        PROMPT.format(topic=topic, existing=existing or "none"), temperature=0.7, max_tokens=3500)
    path = POSTS_DIR / f"{today().isoformat()}-{slugify(data['title'])}.md"
    front = {"title": data["title"], "summary": data["summary"], "tags": data.get("tags", []), "ai_drafted": True}
    path.write_text("---\n" + yaml.safe_dump(front, sort_keys=False, allow_unicode=True) + "---\n\n" +
                    data["body"].strip() + "\n", encoding="utf-8")
    state.setdefault("drafted_topics", []).append(topic)
    save_state(state)
    print(path.relative_to(CONTENT.parent).as_posix())
    return str(path)


if __name__ == "__main__":
    draft(" ".join(sys.argv[1:]) or None)
