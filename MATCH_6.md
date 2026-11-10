# MATCH 6 — Can Your AI Master the Unknown?

Status: Nov 10–14 · worth 2,400 points (highest) · prizes while live
One-liner: "Build an intelligent agent that learns an unfamiliar strategy game,
navigates hidden maps and completes missions efficiently while minimizing compute
and inference tokens."

## Risk first

This match rewards **efficiency under uncertainty** (tokens + compute), not a
polished UI. Without the exact game API it is not buildable ahead of time.
Do not pre-invest; wait for the environment, then timebox.

## Decision rule

- If Match 5 submission is done by **Nov 12** → attempt Match 6 with a 2-day box.
- Otherwise skip; the 2,400 points are not worth losing Match 5 quality.

## Minimal viable approach (if attempted)

1. Read the game spec in the notebook; enumerate actions and observation shape.
2. Baseline: scripted explorer (DFS with a visited set) + safe action filter.
3. Cheap policy layer: heuristics over the observation (no LLM per step).
4. Use the LLM only for planning calls (few, batched) to respect the token score.
5. Log tokens and steps; prefer fewer calls over a stronger policy.
6. Stop-loss: if the environment is not running by day 1 noon, skip.

## Scoring levers (guess, verify)

- Mission completion vs. compute/token budget.
- Deterministic replay and a readable trace.
- Robustness to hidden/partial maps.

## Definition of done (if attempted)

- [ ] Baseline agent completes at least one mission
- [ ] Token/step budget logged and below the naive LLM-per-step baseline
- [ ] One-command run + README
- [ ] Submitted before Nov 14
