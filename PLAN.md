# PLAN — AMD AI League, solo run (Nov 9 → Dec 1, 2026)

## Target (in order of certainty)

| Outcome | Status | Realistic? |
|---|---|---|
| ROCm Certified Associate credential | must | yes |
| Valid Match 4 submission + top-50 credits | must | yes |
| Match 5 submission | should | yes |
| One match cash prize ($500) | stretch | maybe |
| League top-3 cash | drop | no (referral gap) |

Rule: the credential and the portfolio are the return. Match prizes are upside.

## Budget

- 2–3 focused hours/day, 7 days.
- GPU quota: 3h/day on `notebooks.amd.com/hackathon` (idle sessions burn it).
- Individual only: no team, one account, no self-referral.
- Total planned: ~24–30 hours to Dec 1.

## Phase 0 — Today (Nov 9), ~90 min

- [ ] Enroll via lablab SSO with AMD (10m)
- [ ] Onboarding 6 steps: credits, first course, profile, both Discords (40m)
- [ ] Launch notebook, confirm persistent path + quota reset (15m)
- [ ] Read the Match 4 brief in Discord / notebook, note exact format (10m)
- [ ] In repo: `pytest` 11 tests pass (5m)
- [ ] Save screenshots of onboarding + submission page

Output: enrolled, onboarded, brief understood, repo green.

## Phase 1 — Match 4 (Nov 9 → Nov 10), 5–6h

- H1: run the agent on 3 real sites; fix redirects, encodings, nav noise.
- H2: build a 10-question eval; log accuracy, citation-verify rate, pages read.
- H3: wire the LLM path to the AMD OpenAI-compatible endpoint if a key exists;
  keep the labelled extractive fallback for offline runs.
- H4: prove the "not found" path (no hallucination) and a multi-page answer.
- H5: README section + submission in the exact brief format.

Definition of done:
- [ ] 3 sites, 10 questions, 100% citation verification
- [ ] "not found" demonstrated
- [ ] Token/page counts in the report
- [ ] Submitted while live
- [ ] Screenshot confirmation

## Phase 2 — Match 5 (Nov 10 → Nov 12), 6–8h

- Create `examples/broken-repo/` with one fixable bug + one honest unresolved case.
- Implement `src/repo_repair.py`: triage → locate → fix → referee → report.
- Offline tests with a fake LLM returning a known diff.
- One real bug fixed (tests go green), one reported unresolved.
- Submit with trace + README.

Definition of done:
- [ ] Red→green demonstrated
- [ ] Attempt cap (3) respected
- [ ] Trace shows agent roles
- [ ] Submitted while live

## Phase 3 — Nov 12 → Nov 14 (decision window)

- If Match 5 submitted by **Nov 12 noon**: timebox Match 6 to 2 days with a
  stop-loss (skip if the environment is not running by Nov 13 morning).
- If not: **skip Match 6** and use the time for closed Match 2/3 points.
- Closed Match 2 (OCR) and Match 3 (RAG) still award points; each ~2–3h.
- Keep Nov 14 as a re-submission buffer.

## Phase 4 — Nov 14 → Dec 1 (points + credential)

- Course ladder: 1 course/day → 5 by Nov 20 → keep to 10.
- ROCm Certified Associate path (+500 and the badge).
- Publish the repo open-source (+200).
- 2 blog/tutorial posts tagging lablab + AMD (+100 each, max 2/month).
- LinkedIn progress post weekly (+10).
- Discord answers where genuinely helpful.
- Share referral link (points only; no grinding).

## Weekly cadence

| Day | Block |
|---|---|
| Mon | plan + one course + cheap points |
| Tue–Thu | build the live match |
| Fri | submit + verify points posted (updates Fridays) |
| Sat | closed matches / extras |
| Sun | buffer + next-week plan |

## Score projection (planning estimate)

| Item | Points |
|---|---|
| Onboarding (incl. first course) | ~600 |
| Match 4 | 1,800 |
| Match 5 | 2,100 |
| 5-course milestone | 500 |
| ROCm Associate | 500 |
| Open-source + 2 blogs + 4 LinkedIn | ~440 |
| Match 2 + Match 3 (optional) | 2,700 |
| **Total** | **~5,900–8,600** |

Top of the board was 7,350 XP on Nov 9 and is referral-driven. Treat the podium
as out of reach; this plan is built to maximize credential + submissions.

## Progress log — 2026-11-09 (agent pass)

Done in the repo (no enrollment/submission performed):

- [x] `pytest`: 22 offline tests pass (11 original + 9 noise tests + 2 excerpt/retry).
- [x] Real-site runs on 3 sites; redirect (rfc-editor.org), charset, nav/category
      noise, and URL dedupe handled.
- [x] 11-question eval (`eval/questions.json`): **11/11**, 9/9 citations
      verified verbatim, 0 dropped.
- [x] "Not found" proven on 2 questions with zero citations (no hallucination).
- [x] Multi-page run: 4 pages read, quote cited from a linked page.
- [x] LLM path wired (OpenAI-compatible env vars), JSON-fence parsing tested,
      honest fallback labelled when the call fails.
- [x] Live Token Lab run (`DeepSeek-V4-Flash`): **11/11**, 9/9 citations,
      0 dropped; 8 `llm` + 3 grounded fallbacks. Key budget: 10 points/30 days.
- [x] README + `MATCH_4_RESULTS.md` submission evidence.

Still human-only / blocked on the event:

- [ ] Enroll, onboarding 6 steps, claim credits, both Discords, profile.
- [ ] Read the exact Match 4 submission format in Discord / AMD notebook.
- [ ] One run inside `notebooks.amd.com/hackathon`; save output to the
      persistent path; capture the AMD/ROCm evidence.
- [ ] Submit while live, screenshot the confirmation.
- [ ] Teardown the notebook session (idle burns the 3h/day quota).

## Stop rules

- If a match is not runnable 12h before the deadline → submit an honest partial,
  never fake an output.
- Turn off the notebook session when not working (idle burns quota).
- No second account, no self-referral, no team submission.
- Do not pivot mid-match; finish or drop, don't restart.
