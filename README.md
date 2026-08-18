# Pramaana — प्रमाण

**Structural credibility analysis for news articles.**

Paste any article URL. Pramaana returns a structured credibility score across five dimensions — source transparency, claim verifiability, cross-source consensus, narrative honesty, and contextual completeness. Built for South Asian and global geopolitical news.

**Part of**: [Flashpoint](https://flashpoint.watch)

---

## Why this project

Most credibility tools give you a single number derived from domain reputation or fact-checker flags. Pramaana scores the *structure* of individual articles — who is cited, what is missing, who benefits from the framing, whether the editorial voice is disclosed.

The dataset is the long-term value. A single article score is interesting. A thousand articles across hundreds of outlets over years is infrastructure — usable by researchers, journalists, and media critics independently of this tool.

The dataset is version-controlled, human-moderated, and built to be cited and forked.

---

## Self-hosting

Pramaana is fully self-hostable. Bring your own Anthropic API key.

### With Docker

```bash
git clone https://github.com/rachit-mishra/pramaana
cd pramaana
cp .env.example .env        # add your ANTHROPIC_API_KEY
docker-compose up
```

Open http://localhost:8000.

### Without Docker

```bash
git clone https://github.com/rachit-mishra/pramaana
cd pramaana
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required. Get one at [console.anthropic.com](https://console.anthropic.com) |
| `DATABASE_URL` | — | PostgreSQL connection string (recommended for production) |
| `DB_PATH` | `./pramaana.db` | SQLite path — used only when `DATABASE_URL` is not set |
| `PRAMAANA_IP_LIMIT` | `5` | Fresh analyses per IP per 24h |
| `PRAMAANA_GLOBAL_LIMIT` | `100` | Total fresh analyses per 24h |
| `ADMIN_TOKEN` | — | Required to access the moderation UI |

---

## Architecture

Full diagram: [docs/architecture.html](docs/architecture.html)

```
User analyzes article
        ↓
Result stored in DB  ←→  In-memory cache (hot path)
        ↓
status = pending
        ↓
Moderator reviews (outlet name, region, scope, plausibility)
        ↓
status = approved → appears in leaderboard
```

**Database**: PostgreSQL in production (SQLite for local development). Articles are stored with structured columns for outlet, region, and status — not just a JSON blob — so the dataset is queryable independently of the application.

**Seed layer**: `pramaana_data.py` is a version-controlled fixture file — a founding dataset of human-reviewed articles that seeds the database on every fresh deployment. It survives database resets and is auditable via git history.

**Dataset export**: Approved articles are periodically exported to `dataset/articles.json` — a portable, citable snapshot of the dataset that can be used independently of this codebase.

---

## Cost

Each fresh analysis calls Claude Sonnet (~$0.01). Repeated analyses of the same URL are cached — free. Set a [spend limit](https://console.anthropic.com/settings/limits) in the Anthropic console to cap your exposure.

---

## How scoring works

Five dimensions, each scored 0–100. See [METHODOLOGY.md](METHODOLOGY.md) for what each dimension measures, the moderation standards, and the known limitations of LLM-based credibility analysis.

---

## Contributing

- **Submit an article**: analyze it in your self-hosted instance, then click Submit to dataset.
- **Add via PR**: add entries to `pramaana_data.py` following the existing format.
- **Dispute a score**: open a Score Dispute issue with evidence.
- **Code**: fork → branch → PR. Open an issue first for significant changes.

See [CONTRIBUTING.md](CONTRIBUTING.md) for full details.

---

## The case for collaboration

The dataset's value compounds with coverage. An outlet with one article is a data point. An outlet with fifty articles across three years is a credibility profile. Cross-outlet comparison across a shared event becomes meaningful analysis.

No single person can build that dataset. The project is designed so that:
- Every analyzed article is a potential dataset contribution
- Contributions are moderated but low-friction
- The methodology is fully open — scores are contestable and the reasoning is auditable
- The dataset is portable — it doesn't require this tool or this infrastructure to be useful

---

## Stack

- **Backend**: FastAPI + PostgreSQL (SQLite for local dev) + Anthropic Claude
- **Frontend**: vanilla JS, no framework
- **Dataset**: `pramaana_data.py` — version-controlled seed layer; `dataset/articles.json` — exported approved dataset

---

## License

MIT
