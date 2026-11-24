# PortWatch VI Discord relay

Standalone Python 3 relay for public PortWatch VI news and tracker changes. No external Python packages. It polls the upstream public JSON, does not scrape the site, and does not download or forward game binaries. News embeds link to PortWatch VI articles, not external downloads.

## GitHub Actions (no PC needed)

1. Create a new empty repository on your own GitHub account (public for free standard GitHub-hosted runner minutes; private if you prefer and have sufficient Actions minutes). Extract this package and push `relay.py`, `README.md` and the hidden `.github/workflows/portwatch.yml` directory to its default branch. Do not fork the upstream project just for this.
2. In Discord, create a webhook in the desired channel under Integrations. Rotate any previously shared URL if appropriate.
3. In your new GitHub repository, open Settings > Secrets and variables > Actions > New repository secret. Name it `DISCORD_WEBHOOK_URL` and paste the full webhook URL as its value. Never commit it.
4. Open Actions > PortWatch VI Discord relay > Run workflow. The first run sends one online message and commits a baseline without posting old news.
5. The workflow checks every 15 minutes (scheduled runs can be delayed). It saves sent items in `relay-state.json`, including revisions of news articles. Ensure Actions can write repository contents and that branch rules allow its state commits.

A failure to save delivery state after Discord accepts a post can cause duplicates. The source may also truncate its history, so updates removed between polling runs can be missed. News and tracker entries can cover the same development; both are forwarded intentionally. GitHub may disable inactive public scheduled workflows after 60 days. If using a private repo, check Actions usage and your plan's allowance. No live Discord delivery or cloud deployment was tested when packaging this relay.

## Run locally instead

Set `DISCORD_WEBHOOK_URL` in your shell, then run `python3 relay.py` from the extracted directory. For continuous use schedule that command every 15 minutes using Task Scheduler or cron, with the working directory set to this folder. Keep `relay-state.json` to avoid replaying old entries.
