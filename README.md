# AMD AI League — entry workspace

Event: https://lablab.build/ai-hackathons/amd-lablab-ai-academy-challenge
Format: league, **individual only**, Sep 1 – Dec 1 2026, 6 matches, points leaderboard
Sponsor stack: AMD ROCm / AMD Developer Cloud / notebook env, DeepLearning.AI
Status: **Match 4 live** (Intelligent Web Information Retrieval) · Match 5 (Nov) · Match 6 (Nov 10–14)

> This folder is the source of truth for the AMD league entry. Read `STRATEGY.md`
> first, then `POINTS_PLAN.md`. Build code for Match 4 lives in `src/`.

## Match 4 — verified web retrieval agent

The agent reads one or more public pages, answers the request, and attaches a
**verbatim quote + URL** for every claim. A quote that is not literally present
in the fetched page is dropped. When the answer is absent, the agent says
`"Not found on the pages read."` instead of inventing one.

Current evidence (`eval/report.json`, details in `MATCH_4_RESULTS.md`):

- 3 real sites (Wikipedia, Python docs, IETF RFC 2616)
- **11/11 questions passed**, **9/9 citations verified**, 0 dropped
- 2/2 "not found" cases with zero citations
- multi-page run: 4 pages read, answer cited from a linked page
- every run emits a **navigation trace** (`steps`: URL, depth, fetched size,
  links queued, link score, failures) so the site traversal is auditable
- fresh clone, no cache: `python3 eval/run_eval.py --refresh` → 11/11 on
  2026-11-10 (`eval/report_live.json`)
- 24 offline tests passing; recorded runs in `demo/`

### Quickstart (no key needed)

```bash
python3 src/web_retrieval_agent.py \
  --request "What does the 404 status code mean?" \
  --start "https://www.ietf.org/rfc/rfc2616.txt"
```

The JSON result includes the answer, verified citations (URL + verbatim quote),
and a `steps` trace of the navigation.

### With an OpenAI-compatible model (AMD Token Lab)

```bash
# .env is gitignored; never commit it
set -a; . ./.env; set +a
# LLM_BASE_URL=https://api.tokenlab.amd.com/v1
# LLM_API_KEY=<token from notebooks.amd.com Token Lab>
# LLM_MODEL=DeepSeek-V4-Flash
python3 src/web_retrieval_agent.py --request "..." --start https://...
```

If the key is absent, the deterministic extractive answerer runs and the output
is labelled `"engine": "extractive-fallback"`. If a configured LLM call fails
(HTTP 429/5xx are retried), the agent falls back, records `fallback_reason`, and
never fakes a model call. When the LLM returns a citation that does not verify
verbatim, the agent re-answers with the extractive engine instead of shipping a
hallucinated quote (`fallback_reason: "unverified-llm-citation"`). Long pages
are sampled by query-relevant windows, so a late RFC section is not lost to
truncation.

### Eval (reproducible)

```bash
# offline unit tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest src/test_smoke.py -q

# refetch every page (works on a fresh clone; needs network)
python3 eval/run_eval.py --refresh

# replay from eval/cache/ with no network (cache ships only in the dev tree)
python3 eval/run_eval.py --offline
```

`eval/questions.json` holds the 11 questions and expected values.
`eval/report.json` is the last no-key run and `eval/report_llm.json` the last
Token Lab run (`--report eval/report_llm.json`). Both are 11/11 with 9/9
citations verified and 0 dropped. The exit code is non-zero when accuracy is
below 80% or a citation fails verbatim verification.

## Files

| File | Purpose |
|---|---|
| `BRIEF.md` | event rules, prizes, points, infra — verified from the page |
| `STRATEGY.md` | what to play and why, EV, competition math |
| `POINTS_PLAN.md` | exact point checklist + day-by-day |
| `CONCEPT_SCORED.md` | 3 concepts per live match, scored and ranked |
| `MATCH_4.md` | retrieval agent plan: architecture, eval, demo |
| `MATCH_4_RESULTS.md` | Match 4 run report: proof, commands, limits |
| `MATCH_5.md` | repo-repair multi-agent plan |
| `MATCH_6.md` | unknown-game match: risk and minimal approach |
| `SUBMIT_CHECKLIST.md` | per-match and league submission gates |
| `src/web_retrieval_agent.py` | Match 4 agent: fetch → read → answer with verified citations |
| `src/test_smoke.py` | 24 offline tests (fake fetcher, fake LLM, noise, redirects, trace) |
| `eval/questions.json` | 11-question eval set over 3 real sites |
| `eval/run_eval.py` | cached eval runner + report writer |
| `eval/report.json` | last no-key eval result (evidence for the submission) |
| `eval/report_live.json` | fresh-clone network run, 2026-11-10 |
| `demo/*.json` | recorded live runs: multi-page navigation, not-found gate |

## Rules

- One account per person. No teams, no self-referral, no multi-account.
- Matches 2 and 3 are closed for prizes but **still score points**.
- League cash needs top-3 total **and** ≥5 Academy courses.
- GPU: `notebooks.amd.com/hackathon`, 3h/day quota, ~25 GB persistent.
  Save to `/persistent` when the URL contains `jupyter-hack-`, else `/workspace`
  when it contains `rgapi-hackathon-`.
- Never commit `.env`, API keys, or personal data.
