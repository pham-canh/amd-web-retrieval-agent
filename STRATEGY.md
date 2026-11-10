# STRATEGY — where the return actually is

## The honest read

This is a **points league**, not a judged hackathon. Three things follow:

1. The overall podium is **referral-dominated**. Leader at 7,350 XP has 6,750
   from referrals. Starting on Nov 9 with no referral network, top-3 total is
   not a realistic target. Do not plan around the $2,500.
2. Match prizes are **sparse**: 163 submissions across the whole league, 57
   drafts. Top 50 per match is a low bar, and even top-2 is plausible with one
   solid build.
3. The **credential** (ROCm Certified Associate) and the portfolio are the only
   certain returns. They also cost the least time.

## Three objectives, ranked by certainty

| Objective | Certainty | Cost | Why |
|---|---|---|---|
| ROCm Certified Associate badge | high | ~1–2 days of courses | verifiable, issued via Credly, goes on LinkedIn/CV |
| Match 4 / Match 5 prize | medium | 1–2 days each | few submissions, strong fit |
| League cash top-3 | low | weeks + referrals | referral gap is too large now |

## Recommended play (Nov 9 → Nov 14)

1. **Today: onboarding + first course + AMD profile + both Discords** (fast points,
   unlocks match participation).
2. **Do Match 4 now** — it is live and matches the backend/agent skill set. Goal:
   a valid submission, not perfection. Top-50 credits are realistic.
3. **Then Match 5** (code repo repair). Strongest technical fit you have: tests,
   CI, static analysis, patch generation.
4. **Closed Match 2 + 3 for points only** if time remains (1,200 + 1,500).
5. **Start the Academy course ladder** toward 5 courses (needed for any league
   prize) and the ROCm certificate.
6. Skip Match 6 unless Match 5 finishes early; it is a hidden-map strategy game
   with compute/token scoring — high variance.

## Why not grind the leaderboard

- Points are visible and gamified; the top is already 2,000+ XP ahead on
  referrals alone.
- Course milestones cap at 2,500 points total and require real time.
- Match points (1,200–2,400) only move you a few ranks unless you also refer.
- The EV of one match prize ($500 / ~40 submissions) beats weeks of referral
  chasing with no network.

## Risk list

| Risk | Mitigation |
|---|---|
| Match 4 brief differs from the one-liner | read Discord + notebook before finalizing; keep the interface CLI+JSON so it re-wraps |
| GPU quota 3h/day | develop offline, use the notebook only for the AMD-specific run |
| Storage lost on session end | write to `/persistent` or `/workspace` per URL rule from minute one |
| Individual-only rule | do not share an account or submit as a team |
| Points update lag (Fridays) | do not panic if matches do not appear immediately |

## Decision

**Locked:** credential-first, Match 4 now, Match 5 next, ignore Match 6 unless
ahead of schedule. Do not chase leaderboard cash.
