# Security Policy

## Reporting a vulnerability

If you find a security issue in Pramaana (auth bypass, injection, data exposure, or anything that could compromise a self-hosted or the public instance), please **do not open a public GitHub issue**.

Instead, open a private report via [GitHub Security Advisories](https://github.com/rachit-mishra/pramaana/security/advisories/new) for this repository, or reach out directly to the maintainer.

Include:
- A description of the issue and its impact
- Steps to reproduce
- Any relevant logs or screenshots (redact secrets first)

## Scope

- The FastAPI backend (`main.py`, `db.py`)
- The admin moderation panel (`admin.html`) and its auth (`ADMIN_TOKEN`)
- Rate limiting and abuse-prevention logic

## Handling secrets

- Never commit `.env`, API keys, or `ADMIN_TOKEN` values. `.env` is gitignored — keep it that way.
- If you self-host, treat `ADMIN_TOKEN` as a real credential: generate it randomly (`openssl rand -hex 24`), don't reuse it elsewhere, and rotate it if you suspect exposure.
- The public instance's `ANTHROPIC_API_KEY` is never exposed to clients — all Claude calls happen server-side.

## Known limitations (not security bugs, but worth knowing)

- `ADMIN_TOKEN` is a single shared secret with no per-moderator identity. Anyone with the token can approve or reject any article. This is acceptable for a single-admin instance; a multi-moderator identity system is a planned improvement, not yet built.
- Rate limiting is IP-based and keyed off `X-Forwarded-For`. Behind Railway's proxy this is reliable, but it is not a substitute for stronger abuse controls if traffic grows significantly.
