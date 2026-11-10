# SUBMIT CHECKLIST

## League-level (do once, early)

- [ ] Enrolled with AMD SSO
- [ ] Onboarding complete (6 steps)
- [ ] AMD profile complete
- [ ] lablab Discord joined (required)
- [ ] AMD Discord joined
- [ ] $100 GPU credits claimed
- [ ] Notebook access verified at `notebooks.amd.com/hackathon`
- [ ] Persistent path confirmed from the redirected URL (`/persistent` vs `/workspace`)
- [ ] Referral link captured (optional, for the referral board)

## Per-match gate (repeat for 4, then 5, 6)

- [ ] Read the exact brief in Discord / notebook (public page is only one line)
- [ ] Repo public or submission zip prepared per the brief
- [ ] README with one run command
- [ ] Offline tests pass: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest src/ -q`
- [ ] Demo input + expected output captured
- [ ] No keys, no `.env`, no personal data in the repo
- [ ] AMD ROCm / Developer Cloud usage documented (load-bearing)
- [ ] Submit while the match is live (closed = points only, no prize)
- [ ] Screenshot the submission confirmation

## Match 4 specifics

- [ ] 3 real sites tested
- [ ] Every citation verified verbatim against the page
- [ ] "Not found" path demonstrated
- [ ] Token/page counts reported

## Match 5 specifics

- [ ] Seed repo with failing tests
- [ ] One bug fixed, tests green
- [ ] One unresolved case reported honestly
- [ ] Agent-role trace in the report

## Match 6 specifics

- [ ] Only attempted if Match 5 is already submitted
- [ ] Token/step budget logged
- [ ] At least one mission completed

## Never

- [ ] Never fake a model call or a test result
- [ ] Never share an account (individual only)
- [ ] Never commit `.env` or API keys
- [ ] Never submit after the match closes and call it a prize entry
