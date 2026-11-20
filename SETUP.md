# One-time setup (â‰ˆ 1â€“2 hours, then it runs by itself)

Everything below is free. The parts only you can do are account sign-ups and
"Allow" clicks on each platform â€” no tool may type your passwords for you.

## 1. Put the site live (15 min)

1. Create a free GitHub account, e.g. username **casrinivasa** â†’ your site will be
   **https://srini-cfo-ai.github.io**
2. Create a **public** repository named exactly `srini-cfo-ai.github.io`.
3. Push this folder:
   ```
   git remote add origin https://github.com/srini-cfo-ai/srini-cfo-ai.github.io.git
   git push -u origin main
   ```
4. Repo â†’ **Settings â†’ Pages â†’ Source: GitHub Actions**.
5. Repo â†’ **Settings â†’ Actions â†’ General â†’ Workflow permissions**: *Read and write*,
   and tick *Allow GitHub Actions to create and approve pull requests*.
6. Repo â†’ **Actions â†’ "Build site, make videos & cross-post" â†’ Run workflow**.
   The site is live in ~3 minutes.

### Custom domain (optional, not free)
No registrar gives .com/.ai away free. If you want `casrinivasa.com`, buy it at
Cloudflare Registrar (sold at cost, roughly US$10/year for .com; .ai is far dearer),
then in Settings â†’ Pages â†’ Custom domain enter it, and set repo variable
`SITE_URL = https://casrinivasa.com`.

## 2. Connect each channel (add only the ones you want â€” the rest are skipped)

Add values under **Settings â†’ Secrets and variables â†’ Actions â†’ New repository secret**.

| Channel | What to do | Secrets |
|---|---|---|
| **YouTube + Shorts** | Google Cloud Console â†’ new project â†’ enable *YouTube Data API v3* â†’ OAuth consent (External, then *Publish app*) â†’ OAuth client *Desktop* â†’ save JSON as `tools/client_secret.json` â†’ run `python tools/get_youtube_token.py` | `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` |
| **LinkedIn** | linkedin.com/developers â†’ Create app â†’ add products *Share on LinkedIn* + *Sign In with LinkedIn (OpenID)* â†’ redirect URL `http://localhost:8765/callback` â†’ run `python tools/get_linkedin_token.py <id> <secret>` (**repeat every 60 days**) | `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_PERSON_URN` |
| **X (Twitter)** | developer.x.com â†’ Free plan â†’ project/app â†’ *User authentication: Read and write* â†’ generate keys | `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET` |
| **Facebook Page** | Create a Facebook **Page** for your brand â†’ developers.facebook.com â†’ app (type Business) â†’ Graph API Explorer â†’ get a long-lived **Page** token with `pages_manage_posts`, `pages_read_engagement`, `publish_video` | `FB_PAGE_ID`, `FB_PAGE_TOKEN` |
| **Instagram Reels** | Switch Instagram to **Professional (Creator)** and link it to the Facebook Page â†’ same Meta app, add `instagram_basic`, `instagram_content_publish` â†’ get the IG user id | `IG_USER_ID`, `IG_ACCESS_TOKEN` |
| **Threads** | Meta app â†’ add *Threads API* use case â†’ token with `threads_basic`, `threads_content_publish` | `THREADS_USER_ID`, `THREADS_ACCESS_TOKEN` |
| **Bluesky** | bsky.app â†’ Settings â†’ App passwords â†’ create | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` |

Known platform limits (not fixable in code):
- **YouTube**: a new, un-audited API project may have uploads locked to *private*.
  If that happens, apply for the free *YouTube API Services audit* in Google Cloud
  (takes a few weeks); until then set repo variable `YT_PRIVACY=unlisted` or publish manually.
- **LinkedIn** personal tokens last 60 days; rerun the token script.
- **Meta** long-lived tokens last ~60 days unless you use a System User token (Business Manager, free, never expires).

## 3. Write â€” or let the AI write

- **You write:** add a file `content/posts/YYYY-MM-DD-my-title.md` (GitHub web â†’ *Add file*,
  or the GitHub mobile app) and press **Commit**. That is the "publish everywhere" button.
  Future dates are held and published automatically on that day.
- **AI writes:** every Tuesday the *AI writer* drafts a post from `content/topics.yml`
  using an open model and opens a pull request â€” click **Merge** and it goes everywhere.
  Set repo variable `PUBLISH_MODE=auto` to skip even that click (not recommended for a CA's name).

## 4. Fill in your profile

Edit `content/profile.yml` (everything marked TODO-CV). Add `portal/static/photo.jpg`
for your headshot and `portal/static/cv.pdf` + `cv_file: cv.pdf` for a CV download.

## Free tiers this relies on
GitHub Pages + Actions (public repo: unlimited minutes), GitHub Models (free open-model
inference inside Actions), Piper TTS (open-source voice model), FFmpeg, and each
platform's free posting API.
