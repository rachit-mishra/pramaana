# Pramaana — Scoring Methodology

Pramaana scores article credibility across five structural dimensions. The overall score (0–100) is a weighted composite. Scores are assigned by Claude Sonnet based on the prompt in `main.py`; the methodology here defines what each dimension measures so scores are auditable and contestable.

## Score ranges

| Range | Label |
|-------|-------|
| 70–100 | Credible |
| 40–69 | Mixed |
| 0–39 | Low credibility |

---

## Dimensions

### 1. Source Trust (0–100)
Does the outlet have a track record of editorial independence? Are authors named and credentialled? Is funding transparent?

High score: named authors with verifiable expertise, independent editorial board, transparent ownership and funding, published corrections policy.

Low score: state-owned or state-adjacent, anonymous authors, opaque funding, history of retractions without correction.

---

### 2. Claim Verifiability (0–100)
Can the specific factual claims in this article be independently checked?

High score: primary sources cited (government documents, court records, named officials on record), statistics linked to original datasets, events corroborated by contemporaneous reporting.

Low score: unnamed sources only, figures presented without sourcing, events described without corroboration.

---

### 3. Cross-source Consensus (0–100)
Do other credible, independent outlets covering the same story reach compatible conclusions?

High score: core facts corroborated by multiple independent outlets across different editorial alignments.

Low score: framing or facts contradicted by independent reporting; story exists only in ideologically aligned outlets.

---

### 4. Narrative Transparency (0–100)
Does the article clearly signal when it is offering analysis or opinion versus reporting facts? Is the framing's perspective disclosed?

High score: editorial voice clearly labelled, sources of framing bias disclosed, competing interpretations acknowledged.

Low score: opinion embedded in news framing, editorial stance presented as neutral fact, beneficiaries of the narrative not disclosed.

---

### 5. Contextual Completeness (0–100)
Does the article provide the context a reader would need to evaluate the claims?

High score: historical background included, relevant counter-evidence addressed, limitations of the analysis acknowledged.

Low score: key facts that would complicate the narrative are absent; no historical context; cherry-picked data without acknowledgment of broader trends.

---

## What Pramaana does not measure

- **Political alignment** — a left-leaning or right-leaning outlet is not penalised for its editorial position; it is assessed on whether that position is disclosed and argued transparently.
- **Accuracy of predictions** — Pramaana scores the credibility of the reporting, not whether subsequent events proved the article right.
- **Popularity or reach** — a viral article is not more credible than an obscure one.

---

## Limitations

- Pramaana uses an LLM (Claude) to assess credibility. LLMs have knowledge cutoffs, can hallucinate, and carry their own training biases. Scores should be treated as a structured starting point for analysis, not a ground truth.
- The leaderboard averages scores across a small dataset. Outlets with one article are not statistically representative.
- The model has stronger coverage of English-language outlets and South Asian media than of regional-language outlets.

---

## Contributing a correction

If you believe a score is wrong, open an issue with:
1. The article URL
2. The dimension you believe is mis-scored
3. Evidence (links, primary sources)

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full process.
