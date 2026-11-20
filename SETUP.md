# One-time setup (≈ 1–2 hours, then it runs by itself)

Everything below is free. The parts only you can do are account sign-ups and
"Allow" clicks on each platform — no tool may type your passwords for you.

## 1. Put the site live (15 min)

1. Create a free GitHub account, e.g. username **casrinivasa** → your site will be
   **https://casrinivasa.github.io**
2. Create a **public** repository named exactly `casrinivasa.github.io`.
3. Push this folder:
   ```
   git remote add origin https://github.com/casrinivasa/casrinivasa.github.io.git
   git push -u origin main
   ```
4. Repo → **Settings → Pages → Source: GitHub Actions**.
5. Repo → **Settings → Actions → General → Workflow permissions**: *Read and write*,
   and tick *Allow GitHub Actions to create and approve pull requests*.
6. Repo → **Actions → "Build site, make videos & cross-post" → Run workflow**.
   The site is live in ~3 minutes.

### Custom domain (optional, not free)
No registrar gives .com/.ai away free. If you want `casrinivasa.com`, buy it at
Cloudflare Registrar (sold at cost, roughly US$10/year for .com; .ai is far dearer),
then in Settings → Pages → Custom domain enter it, and set repo variable
`SITE_URL = https://casrinivasa.com`.

## 2. Connect each channel (add only the ones you want — the rest are skipped)

Add values under **Settings → Secrets and variables → Actions → New repository secret**.

| Channel | What to do | Secrets |
|---|---|---|
| **YouTube + Shorts** | Google Cloud Console → new project → enable *YouTube Data API v3* → OAuth consent (External, then *Publish app*) → OAuth client *Desktop* → save JSON as `tools/client_secret.json` → run `python tools/get_youtube_token.py` | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` |
| **LinkedIn** | linkedin.com/developers → Create app → add products *Share on LinkedIn* + *Sign In with LinkedIn (OpenID)* → redirect URL `http://localhost:8765/callback` → run `python tools/get_linkedin_token.py <id> <secret>` (**repeat every 60 days**) | `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN` |
| **X (Twitter)** | developer.x.com → Free plan → project/app → *User authentication: Read and write* → generate keys | `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET` |
| **Facebook Page** | Create a Facebook **Page** for your brand → developers.facebook.com → app (type Business) → Graph API Explorer → get a long-lived **Page** token with `pages_manage_posts`, `pages_read_engagement`, `publish_video` | `FB_PAGE_ID`, `FB_PAGE_TOKEN` |
| **Instagram Reels** | Switch Instagram to **Professional (Creator)** and link it to the Facebook Page → same Meta app, add `instagram_basic`, `instagram_content_publish` → get the IG user id | `IG_USER_ID`, `IG_ACCESS_TOKEN` |
| **Threads** | Meta app → add *Threads API* use case → token with `threads_basic`, `threads_content_publish` | `THREADS_USER_ID`, `THREADS_ACCESS_TOKEN` |
| **Bluesky** | bsky.app → Settings → App passwords → create | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` |

Known platform limits (not fixable in code):
- **YouTube**: a new, un-audited API project may have uploads locked to *private*.
  If that happens, apply for the free *YouTube API Services audit* in Google Cloud
  (takes a few weeks); until then set repo variable `YT_PRIVACY=unlisted` or publish manually.
- **LinkedIn** personal tokens last 60 days; rerun the token script.
- **Meta** long-lived tokens last ~60 days unless you use a System User token (Business Manager, free, never expires).

## 3. Write — or let the AI write

- **You write:** add a file `content/posts/YYYY-MM-DD-my-title.md` (GitHub web → *Add file*,
  or the GitHub mobile app) and press **Commit**. That is the "publish everywhere" button.
  Future dates are held and published automatically on that day.
- **AI writes:** every Tuesday the *AI writer* drafts a post from `content/topics.yml`
  using an open model and opens a pull request — click **Merge** and it goes everywhere.
  Set repo variable `PUBLISH_MODE=auto` to skip even that click (not recommended for a CA's name).

## 4. Fill in your profile

Edit `content/profile.yml` (everything marked TODO-CV). Add `portal/static/photo.jpg`
for your headshot and `portal/static/cv.pdf` + `cv_file: cv.pdf` for a CV download.

## Free tiers this relies on
GitHub Pages + Actions (public repo: unlimited minutes), GitHub Models (free open-model
inference inside Actions), Piper TTS (open-source voice model), FFmpeg, and each
platform's free posting API.
