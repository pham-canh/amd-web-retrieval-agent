# CONCEPT_SCORED — what to build for the live matches

Scoring uses the four idea tests:
1. 24h core loop
2. underserved niche user
3. ≤3 screens
4. previously impossible, not just faster
Bonus: the sponsor stack (AMD/ROCm) must be load-bearing.

The matches are graded by AMD's evaluator, so the demo must be **machine-checkable**:
deterministic output, citations, and a runnable entry point matter more than UI.

## Match 4 — Intelligent Web Information Retrieval

### Concept A (recommended) — "Verified Answer Agent"

- Problem (1 sentence): People ask one precise question and get an answer they
  cannot trust, because the agent does not show the exact sentence it came from.
- User: analyst/compliance reviewer who must cite a public web page.
- Core loop: request + start URL → fetch → read → answer **with verbatim quote +
  URL per claim** → reject any quote not present on the page.
- 3 screens: input form · answer with inline citations · evidence trace.
- Sponsor twist: runs on AMD ROCm notebook; LLM call through AMD-hosted
  OpenAI-compatible endpoint; deterministic fallback when no key.
- Demo risk: low (stdlib fetch + parser; tests offline).
- Score: 4/4.

### Concept B — "Multi-site price/plan comparison"

- Problem: plans and prices are scattered across vendor sites with different units.
- User: procurement lead comparing SaaS plans.
- Core loop: 2–5 URLs → extract normalized table (price, unit, limits) → cite each cell.
- Demo risk: medium (heterogeneous pages, normalization).
- Score: 3/4 (24h risk on normalization).

### Concept C — "Form-filler browser agent"

- Problem: repetitive public web forms (permits, registrations) eat hours.
- User: small-business owner filing a routine permit.
- Core loop: Playwright drives the site, screenshots each step.
- Demo risk: high (JS-heavy, bot walls, quota).
- Score: 2/4.

**Recommendation:** Concept A. It is the closest literal reading of the match
("navigate websites, understand a request, accurately retrieve the specific
information") and the easiest to grade.

## Match 5 — AI-Powered Code Repository Repair

### Concept A (recommended) — "Red → Green Multi-Agent"

- Problem: a failing test suite tells you *what* broke, not *why* or *how to fix it*.
- User: maintainer of a mid-size Python repo without time to bisect.
- Core loop: run tests → parse failures → locate symbols (grep/AST) → propose
  patch → re-run tests → report pass/fail delta.
- 3 screens: failing tests · root cause · patch diff + re-run result.
- Sponsor twist: AMD GPU for the model; deterministic test runner is the referee.
- Demo risk: low–medium (needs a seed repo with one injected bug).
- Score: 4/4.

### Concept B — "Static-analysis triage board"

- Problem: linters emit hundreds of findings that no one triages.
- Core loop: parse ruff/bandit output → group by root cause → ranked fix list.
- Demo risk: low, but weaker "multi-agent" story.
- Score: 3/4.

### Concept C — "Dependency/CVE upgrade bot"

- Problem: security advisories require coordinated multi-file upgrades.
- Core loop: scan requirements → propose bump → run tests → patch breakages.
- Demo risk: medium (network + version resolution).
- Score: 3/4.

**Recommendation:** Concept A. It has a verifiable signal (tests go green), which
matches "minimal human intervention" exactly.

## Match 6 — Can Your AI Master the Unknown?

- Hidden-map strategy game with compute/token scoring.
- Core loop in 24h: scripted explorer + heuristic policy + token budget guard.
- Risk: high; scoring rewards efficiency, not just winning.
- **Defer** unless Match 5 is submitted before Nov 12.
