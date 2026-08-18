# Contributing to Pramaana

Pramaana is a community-built credibility dataset. The tool is a means; the dataset is the end. Every approved article makes the leaderboard more representative and the project more useful to journalists, researchers, and readers.

There are three ways to contribute:

---

## 1. Submit an article via the tool

Analyze any article at your self-hosted instance. After the result appears, click **Submit to dataset** to flag it for moderation review. A moderator will check outlet name, region, scope, and plausibility before it appears on the leaderboard.

This is the primary growth path — the dataset expands from real usage, not just from people editing code.

---

## 2. Add an article via pull request

For contributors who want to add multiple articles, write detailed notes, or contribute to the founding seed layer in `pramaana_data.py`.

### Before submitting

1. Run the article through your self-hosted instance (see README for setup).
2. Read the generated analysis carefully. If any factual claim in the analysis is wrong, do not submit — open a Score Dispute issue instead.
3. Verify the URL is publicly accessible (not paywalled, not returning a 404).
4. Check that the article is not already in `pramaana_data.py` or the approved dataset.

### Article requirements

- Published within the last 12 months
- English language
- Covers geopolitics, governance, conflict, or media criticism
- From a named outlet with a track record (no anonymous blogs, no single-article sites)

### Region field

| Value | When to use |
|-------|-------------|
| `"india"` | India-specific coverage or Indian outlets |
| `"global"` | International/multilateral stories |
| `"official"` | Government or institutional communication — excluded from leaderboard, stays in showcase |

### PR format

Title: `dataset: add [Outlet Name] — [Article headline]`

In the PR description:
- Why this article is a useful credibility case study
- Whether the generated score seems accurate, and any notes on edge cases
- Confirmation that the URL is publicly accessible

---

## 3. Dispute a score

If you believe a dimension score is wrong or the analysis contains a factual error, open a **Score Dispute** issue. Include:

1. The article URL
2. The dimension(s) you believe are mis-scored
3. Specific evidence — links, primary sources, contemporaneous reporting

Score disputes with evidence are reviewed. If warranted, a fresh analysis is run and replaces the original. The dispute and resolution are recorded in the issue for transparency.

Score disputes based solely on disagreement with the conclusion (without evidence) will be closed.

---

## Code contributions

Standard flow: fork → branch → PR. Keep PRs focused — one concern per PR.

For significant changes (new scoring dimensions, new API routes, schema changes, frontend redesign), open an issue first to align before building.

### Running locally

```bash
git clone https://github.com/rachit-mishra/pramaana
cd pramaana
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
uvicorn main:app --reload
```

Open http://localhost:8000.

### With Docker

```bash
cp .env.example .env
docker-compose up
```

---

## What makes a good dataset contribution

The dataset's long-term value is in coverage breadth and political balance. Articles that are most useful:

- Cover the same event from outlets with different editorial alignments (cross-source comparison becomes richer)
- Come from outlets not yet represented in the leaderboard
- Are from the current or recent news cycle (fresh context for the AI)
- Represent regional or language-specific outlets underrepresented in the dataset

Articles that are least useful:
- Duplicate coverage of stories already well-represented
- From outlets with a single article that isn't representative of their normal output
- Opinion pieces from individual columnists that don't reflect the outlet's institutional voice

---

## Moderation standards

Every user-submitted article goes through a moderation step before appearing in the leaderboard. Moderators check outlet canonicalisation, region tagging, scope, plausibility, URL validity, and submission integrity. See [METHODOLOGY.md](METHODOLOGY.md) for the full moderation criteria.

Moderation is not a values judgement on the outlet's politics. An article from a strongly partisan outlet that is transparent about its framing can score well. An article from a prestigious outlet that buries opinion inside news framing can score poorly.
