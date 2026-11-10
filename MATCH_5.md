# MATCH 5 — AI-Powered Code Repository Repair

Status: Nov (confirm dates) · worth 2,100 points · prizes while live
One-liner: "Build a multi-agent AI system that analyzes code, detects defects and
proposes fixes with minimal human intervention."

## Design goal

A red→green loop: take a repo with a failing test suite, localize the defect,
propose a patch, re-run the tests, and report the delta. The test runner is the
referee, so success is machine-checkable.

## Multi-agent roles (each a deterministic step, not a chat)

| Agent | Job | Output |
|---|---|---|
| Triager | run tests, parse failures, rank by blast radius | failing test list + traces |
| Locator | grep/AST search around failing symbols | candidate files + line ranges |
| Fixer | propose patch (LLM), constrained to candidates | unified diff |
| Referee | apply patch, re-run tests | pass/fail delta |
| Reporter | summarize root cause + patch + evidence | markdown report |

## Guardrails

- Patch only inside the located candidate files.
- Max N repair attempts (default 3), then stop and report.
- No network during tests.
- Never claim success without a green re-run; otherwise report "unresolved".

## Seed scenario (demo)

Create `examples/broken-repo/` with one injected bug (e.g., off-by-one in a
pagination function) and a test that fails. The agent must fix it and show tests
going green. Add a second failure it cannot fix to demonstrate the honest stop.

## Build order

1. `examples/broken-repo/` with 2 failing tests (one fixable, one not).
2. `src/repo_repair.py`: triage → locate → fix → referee → report.
3. Offline tests using a fake LLM that returns a known diff.
4. Run on the AMD notebook for the LLM call; keep the test runner local.
5. Demo: failing run → agent trace → patch → green run.

## Definition of done

- [ ] Repo with reproducible failing tests
- [ ] One real bug fixed (tests go green)
- [ ] One unresolved case reported honestly
- [ ] Trace shows agent roles and attempts
- [ ] README with one command
- [ ] Submitted before the match closes
