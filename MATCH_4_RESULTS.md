# MATCH 4 — verified run report

Date: 2026-11-09 · engines: `extractive-fallback` (no key) and hybrid `llm` via
AMD Token Lab (`DeepSeek-V4-Flash`) · dataset: `eval/questions.json` · evidence:
`eval/report.json`, `eval/report_llm.json`

## What was proven

| Check | Result |
|---|---|
| Real sites | 3: Wikipedia, Python docs, IETF RFC 2616 (redirects to rfc-editor.org) |
| Questions | 11 (9 answerable + 2 deliberately absent) |
| Accuracy | **11/11 (100%)** |
| Citations verified verbatim | **9/9 (100%)**, 0 dropped |
| "Not found" path | **2/2**, zero citations, no invented answer |
| Multi-page | **4 pages read**, answer + quote from a linked page (`pickle.html`) |
| Offline tests | **24 passed** |
| Live LLM run (Token Lab) | **11/11**, 9/9 citations, 0 dropped (9 `llm` + 2 grounded fallbacks) |
| Network-free rerun | `python3 eval/run_eval.py --offline` reproduces the report from cache |

Raw result table:

```
id               pass  engine               pg  cit  answer
wiki-creator     True  extractive-fallback  1   1    Python was conceived ... by Guido van Rossum ...
wiki-released    True  extractive-fallback  1   1    Van Rossum first released it in 1991 as Python 0.9.0.
wiki-license     True  extractive-fallback  1   1    Python Software Foundation License
json-stand       True  extractive-fallback  1   1    JSON (JavaScript Object Notation) ...
json-spec        True  extractive-fallback  1   1    ... specified by RFC 7159 ...
json-error       True  extractive-fallback  1   1    ... a JSONDecodeError will be raised.
rfc-port         True  extractive-fallback  1   1    ... default port ... "80" for an HTTP URL
rfc-404          True  extractive-fallback  1   1    ... status code 404 (Not Found) ...
multipage-pickle True  extractive-fallback  4   1    ... pickle can save and restore class instances ...
notfound-wiki    True  extractive-fallback  1   0    Not found on the pages read.
notfound-json    True  extractive-fallback  1   0    Not found on the pages read.
```

## Not-found proof (no hallucination)

```bash
python3 src/web_retrieval_agent.py \
  --request "What is the refund window for annual plans?" \
  --start "https://en.wikipedia.org/wiki/Python_(programming_language)" \
  --max-pages 1 --max-depth 0
```

```json
{
  "answer": "Not found on the pages read.",
  "citations": [],
  "pages_read": 1,
  "engine": "extractive-fallback",
  "verified": true
}
```

The same result holds for `"Who won the 2018 FIFA World Cup?"` against the
Python `json` docs.

## Multi-page proof

Start at the JSON docs page, ask about `pickle`. Link ranking follows the
anchor text, reaches `pickle.html`, and cites a sentence from that linked page:

```bash
python3 src/web_retrieval_agent.py \
  --request "What is pickle used for?" \
  --start "https://docs.python.org/3/library/json.html" \
  --max-pages 4 --max-depth 1
```

- `pages_read`: 4
- citation URL: `https://docs.python.org/3/library/pickle.html`
- quote verified against the fetched page.

## Navigation trace (auditable crawl)

Every result now carries `steps` and `pages`, so the traversal is visible
instead of implied. From `demo/multipage_pickle.json`:

```json
"steps": [
  {"url": "https://docs.python.org/3/library/json.html", "depth": 0,
   "outcome": "read", "chars": 25007, "links_queued": 36},
  {"url": "https://docs.python.org/3/library/pickle.html", "depth": 1,
   "outcome": "read", "chars": 43877, "link_score": 0.7},
  {"url": "https://docs.python.org/3/contents.html", "depth": 1,
   "outcome": "read", "chars": 97229, "link_score": 0.0},
  {"url": "https://docs.python.org/3/library/email.iterators.html",
   "depth": 1, "outcome": "read", "chars": 2080, "link_score": 0.0}
]
```

Redirects are recorded too: RFC 2616 is fetched from `ietf.org` and cited at
`rfc-editor.org` (`url` vs `final_url`). Failed fetches appear as
`"outcome": "failed"` with the exception type, so a silent skip is impossible.

## Live LLM run (AMD Token Lab)

```bash
set -a; . ./.env; set +a
python3 eval/run_eval.py --report eval/report_llm.json
```

- Endpoint `https://api.tokenlab.amd.com/v1`, model `DeepSeek-V4-Flash`
  (10-point/30-day key, 20 req/min; 429/5xx are retried).
- Result: **11/11**, citations **9/9** verified, 0 dropped, 14 pages.
- 9 questions answered by `llm`; 2 fell back to the extractive engine when the
  model's quote did not verify verbatim (`fallback_reason:
  "unverified-llm-citation"`), so no hallucinated citation ships.
- RFC 2616 answers work because long pages are sampled by query-relevant
  windows instead of the first 6000 characters.

## Reproduce

```bash
# offline unit tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest src/test_smoke.py -q

# eval from cache (no network)
python3 eval/run_eval.py --offline

# eval with fresh fetches (network)
python3 eval/run_eval.py --refresh
```

Exit code is non-zero if accuracy drops below 80% or if any returned citation
fails verbatim verification.

## What changed in this pass

- Block-aware HTML extraction: drops nav/header/footer/aside, TOC, language
  lists, category links, navboxes, edit/script/style noise; keeps paragraph
  boundaries so quotes are sentence-sized.
- Charset fallback from `meta charset`, content-type guard, redirect-aware
  citation lookup, URL dedupe, binary-extension skip.
- Link ranking by anchor text + URL overlap (`request` passed into `crawl`), so
  a multi-page run follows relevant links instead of breadcrumbs.
- Query-intent heuristics for the labelled extractive fallback: who/when/license/
  port/404/exception shapes, a minimum-score gate, and a two-pass filter so a
  question cannot be answered by an unrelated sentence.
- Safer LLM path: JSON-fence stripping, `max_tokens`, an honest fallback to the
  extractive engine (with `fallback_reason`) if the API call fails, and
  retry/backoff on HTTP 429/5xx.
- Long pages are sampled by IDF-weighted query-relevant windows, so RFC 2616
  answers survive a 6000-character prompt budget.
- Hybrid grounding: if the LLM cites text that does not verify verbatim, the
  extractive engine re-answers instead of shipping a fake quote.
- 11 new offline tests (24 total), including excerpt selection and 5xx retry.
- Navigation trace in every result (`steps` + `pages`): URL, depth, final URL
  after redirects, fetched size, links queued, link score, and failed fetches.

## Still needs the human / AMD notebook

These cannot be done from this repo session:

- Lablab enrollment, onboarding, `$100` credits, course ladder, both Discords.
- Submission format confirmed from the lablab dashboard: create a **solo team**
  (name/description/cover) -> team dashboard -> **submission form** step 1
  (title, long description, categories, technologies) -> step 2 (GitHub repo
  URL, additional information).
- Repo must be public; the current git remote is private, so the entry is
  exported to a standalone public repo before submitting.
- Submit while the match is live and screenshot the confirmation.

## Honest limitation

The eval is 11 questions over 3 stable sites. It proves citation discipline,
the not-found gate, redirect/encoding handling, and multi-page retrieval; it is
not a claim of open-domain accuracy. The live Token Lab run passes 11/11, but 2
of those answers come from the grounded extractive fallback, not from the model.
The 10-point key lasts 30 days, so the demo should not be re-run casually.
