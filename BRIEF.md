# BRIEF — AMD AI League (lablab.build)

Verified from the event page on 2026-11-09. Anything not on the page is marked
"verify".

## Identity

- Name: **AMD AI League** (page subtitle: "AMD AI League Preview — Cascade Clean")
- URL: https://lablab.build/ai-hackathons/amd-lablab-ai-academy-challenge
- Presented by: AMD × NativelyAI × lablab.ai
- Format: **league, not a 48h hackathon** — 6 matches, one cumulative leaderboard
- Participation: **individual only** (no teams)
- Window: **Sep 1 – Dec 1, 2026**; final match ends **Nov 14**; league concludes Dec 1
- Prizes: **$10,000+**

## Prizes

| Track | 1st | 2nd | 3rd | Notes |
|---|---|---|---|---|
| League podium (total points) | $2,500 cash | $1,500 cash | $1,000 cash | must finish ≥5 Academy courses |
| Each match | $500 cash | $250 AMD GPU credits | top-50 get $100 credits | prizes only while the match is live |
| Referral leaders | $1,000 | $600 | $400 | ranked by qualified friends |

Closed matches still award points, but no prizes.

## Points

| Activity | Points |
|---|---|
| Onboarding (6 steps) | +300 |
| Claim $100 AMD GPU credits | +100 |
| First AMD AI Academy course | +100 |
| Complete AMD profile | +50 |
| Join lablab Discord | required for matches (no points shown) |
| Join AMD Discord | +50 |
| Complete 5 / 10 / 20 / 25 courses | +500 each |
| ROCm Certified Associate | +500 |
| Referral (join / first course / submit) | +50 / +100 / +100 (max +250 per friend) |
| Match 2 OCR | +1,200 (closed for prizes) |
| Match 3 RAG | +1,500 (closed for prizes) |
| Match 4 Web information retrieval | +1,800 (**live**) |
| Match 5 Code repository repair | +2,100 (Nov) |
| Match 6 Unknown strategy game | +2,400 (Nov 10–14) |
| Publish open-source project | +200 |
| Blog/tutorial tagging lablab + AMD | +100 (max 2/month) |
| LinkedIn progress post | +10 (max 1/week) |
| Discord answer/like/accepted | +5 / +2 / +50 |

Points update every Friday with activity through Wednesday.

## Matches

| # | Name | Status | Task |
|---|---|---|---|
| 1 | Get Started With AMD | closed | connect AMD account, claim credits, intro tutorial |
| 2 | Optical Character Recognition | closed | image → text with a vision/VLM model |
| 3 | Retrieval-Augmented Generation | closed | container answering from a mixed corpus, return source files |
| 4 | Intelligent Web Information Retrieval | **live** | agent navigates websites, resolves a natural-language request, retrieves exact info |
| 5 | AI-Powered Code Repository Repair | Nov | multi-agent analyzes code, detects defects, proposes fixes |
| 6 | Can Your AI Master the Unknown? | Nov 10–14 | agent learns an unfamiliar strategy game, hidden maps, minimize compute/tokens |

Match 4's "View match details" link points back to the event page; no separate
public brief was found. **Verify the submission format in the lablab Discord or
the AMD notebook before locking the interface.**

## Infrastructure

- GPU: `notebooks.amd.com/hackathon` → AMD Developer Program SSO → "Launch Notebook"
- Quota: **3 hours running time per day**, resets every 24h; idle sessions still burn quota
- Storage: ~25 GB persistent
  - URL contains `jupyter-hack-***` → save under `/persistent`
  - URL contains `rgapi-hackathon-***` → save under `/workspace`
- You do **not** need your own AMD hardware or Fireworks keys for a match.
- Stack usage on the live board (Match 4 round): AMD ROCm 124, AMD Developer
  Cloud 80, HuggingFace Hub 52, Antigravity 35, AI/ML API 31, Claude 28, Qwen3 25.

## Snapshot at 2026-11-09

- Participants: 6,580 (+28/day)
- "Teams": 2,713 (display only — rules say individual)
- Submissions: 163 (+3/day); drafts in progress: 57
- Top XP is referral-driven (leader 7,350 XP, 6,750 from referrals)
- Notes: leaderboard XP shown is "AMD Quest" partial standings, not necessarily
  the Match-4 judge score.

## Deadline pressure

- Today: Nov 9. Match 4 is live **now**.
- Match 6 opens Nov 10 and runs to Nov 14.
- Match 5 is listed only as "Nov" — confirm dates in Discord.
- League points continue to Dec 1 via courses/referrals/posts even after Nov 14.
