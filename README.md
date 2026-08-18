# Pramaana — प्रमाण

**Structural credibility analysis for news articles.**

Paste any article URL. Pramaana returns a structured credibility score across five dimensions — source transparency, claim verifiability, cross-source consensus, narrative honesty, and contextual completeness. Built for South Asian and global geopolitical news.

**Part of**: [Flashpoint](https://flashpoint.watch)

---

## Self-hosting

Pramaana is fully self-hostable. Bring your own Anthropic API key — you control the spend and the data.

### With Docker (recommended)

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
cp .env.example .env        # add your ANTHROPIC_API_KEY
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required. Get one at [console.anthropic.com](https://console.anthropic.com) |
| `PRAMAANA_IP_LIMIT` | `5` | Fresh analyses per IP per 24h |
| `PRAMAANA_GLOBAL_LIMIT` | `100` | Total fresh analyses per 24h |
| `DB_PATH` | `./pramaana.db` | SQLite database path |

---

## Cost

Each fresh analysis calls Claude Sonnet (~$0.01). Repeated analyses of the same URL are cached — free. The public instance has a daily cap; self-hosted instances only spend when you do.

Set a [spend limit](https://console.anthropic.com/settings/limits) in the Anthropic console to cap your exposure.

---

## How scoring works

Five dimensions, each scored 0–100. See [METHODOLOGY.md](METHODOLOGY.md) for what each dimension measures, what high and low scores mean, and the known limitations of LLM-based credibility analysis.

---

## Contributing

- **Add an article**: run it through Pramaana, review the output, open a PR against `pramaana_data.py`. See [CONTRIBUTING.md](CONTRIBUTING.md).
- **Dispute a score**: open an issue with the article URL and evidence. See the Score Dispute issue template.
- **Code**: fork → branch → PR. Open an issue first for anything significant.

---

## Stack

- **Backend**: FastAPI + SQLite + Anthropic Claude
- **Frontend**: vanilla JS, no framework
- **Dataset**: `pramaana_data.py` — human-reviewed, version-controlled

---

## License

MIT
