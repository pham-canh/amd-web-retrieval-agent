# MATCH 4 — Intelligent Web Information Retrieval

Status: **LIVE** · worth 1,800 points · prizes $500 / $250 credits / top-50 $100 credits
One-liner from the event page: "Build an AI agent that can navigate websites,
understand a natural-language request and accurately retrieve the specific
information a user needs."

> The public brief is only the one-liner. Confirm the exact submission format in
> the lablab Discord / AMD notebook before the final submit.

## Design goal

Answer a natural-language request from one or more web pages, and make every
claim **verifiable**: each answer carries the URL and the exact quoted sentence,
and the agent rejects any quote that does not literally appear on the fetched page.

## Interface (keeps it judge-friendly)

Input:

```json
{"request": "What is the refund window for annual plans?",
 "start_urls": ["https://example.com/pricing"]}
```

Output:

```json
{"answer": "...",
 "citations": [{"url": "https://example.com/pricing",
                "quote": "Annual plans can be refunded within 30 days."}],
 "pages_read": 3, "engine": "llm|extractive-fallback", "verified": true}
```

CLI: `python3 src/web_retrieval_agent.py --request ... --start ...`

## Pipeline

```
start_urls
  -> guard (scheme, host allowlist, max pages, max bytes, timeout)
  -> fetch + follow same-host links up to depth/limit
  -> extract visible text (drop script/style/nav noise)
  -> chunk (paragraph windows)
  -> answerer: LLM (OpenAI-compatible, AMD-hosted) OR deterministic fallback
  -> citation verifier: quote must be substring of page text (normalized)
  -> JSON out; unverified citations are dropped, confidence recomputed
```

## Load-bearing AMD

- The notebook runs on an AMD ROCm GPU node.
- The LLM call goes to an OpenAI-compatible endpoint (AMD Developer Cloud /
  Fireworks-style), configured by env vars — never committed.
- If the key is absent, the extractive fallback runs and is **labelled** in the
  output (`"engine": "extractive-fallback"`), so the demo never fakes an LLM.

## Scoring levers (guess, verify)

- Accuracy of the retrieved value.
- Citation correctness (quote actually on the page).
- Efficiency: pages fetched, tokens used, wall time.
- Robustness: multi-page, redirects, missing answer → says "not found" instead
  of hallucinating.

## Build order (aim: one working run today)

1. `src/web_retrieval_agent.py` skeleton — fetch, parse, chunk, verify. **Done.**
2. `src/test_smoke.py` — offline tests with fake fetcher/LLM. **Done.**
3. Add a real LLM path behind env vars + a 5-URL eval set.
4. Run inside `notebooks.amd.com/hackathon` on the GPU node; save output JSON.
5. Record a 60–90s demo (request → answer → click citation → source sentence).
6. Submit with repo link + a short README section.

## Demo script (60–90s)

1. Show the request and the start URL.
2. Run the CLI; show the answer and the citation.
3. Open the cited URL and highlight the quoted sentence.
4. Show a second request where the answer is not on the page → agent says
   "not found" (no hallucination).
5. Mention efficiency: N pages read, M tokens, and the AMD notebook.

## Definition of done

- [ ] Valid run on 3 different public sites
- [ ] 100% of output citations verified against fetched text
- [ ] "not found" path demonstrated
- [ ] Tests pass offline
- [ ] Repo has README + run command
- [ ] Submitted before the match closes
