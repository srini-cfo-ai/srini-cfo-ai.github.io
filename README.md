# CA Srinivasa Reddy Kareti — personal brand portal

Static site + fully automated content engine, running free on GitHub.

```
content/posts/*.md  ──push──▶  GitHub Actions
                                 ├─ open LLM (GitHub Models: Llama/Mistral/Phi) → video scripts + per-platform copy
                                 ├─ Piper TTS (open voice model) + Pillow + FFmpeg → long.mp4 (16:9) + short.mp4 (9:16)
                                 ├─ build site → GitHub Pages
                                 └─ post → YouTube, YouTube Shorts, LinkedIn, X, Facebook, Instagram Reels, Threads, Bluesky
weekly cron ─▶ AI writer drafts a post → pull request → Merge = publish everywhere
```

Local commands (Windows):

```
python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt piper-tts
.\.venv\Scripts\python -m portal.build            # site → _site/
.\.venv\Scripts\python -m portal.publish prepare  # AI copy + videos for new posts
.\.venv\Scripts\python -m portal.publish status   # what was posted where
```

See **SETUP.md** for the one-time account connections.
