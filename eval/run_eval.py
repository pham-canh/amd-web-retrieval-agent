#!/usr/bin/env python3
"""Run the Match 4 eval over the question set and write a JSON report.

Fetching is cached so a live result stays reproducible offline:

    python3 eval/run_eval.py              # use cache, fetch anything missing
    python3 eval/run_eval.py --refresh    # refetch every page
    python3 eval/run_eval.py --offline    # fail instead of touching the network

Exit code is non-zero when accuracy is below --min-accuracy or when any
returned citation fails verbatim verification against the fetched page.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SRC = PROJECT / "src"
sys.path.insert(0, str(SRC))

from web_retrieval_agent import (  # noqa: E402
    Agent,
    Page,
    build_answerer,
    fetch,
    normalize,
    verify_citations,
)

CACHE_DIR = ROOT / "cache"


def _cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    return CACHE_DIR / f"{digest}.json"


def _page_to_dict(page: Page) -> dict:
    return {
        "url": page.url,
        "final_url": page.final_url,
        "status": page.status,
        "html": page.html,
        "text": page.text,
        "blocks": list(page.blocks or ()),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _page_from_dict(data: dict) -> Page:
    return Page(
        url=data["url"],
        final_url=data["final_url"],
        status=data["status"],
        html=data.get("html", ""),
        text=data.get("text", ""),
        blocks=tuple(data.get("blocks") or ()),
    )


def cached_fetch(url: str, *, refresh: bool, offline: bool) -> Page:
    path = _cache_path(url)
    if path.exists() and not refresh:
        return _page_from_dict(json.loads(path.read_text(encoding="utf-8")))
    if offline:
        raise RuntimeError(f"cache miss in --offline mode: {url}")
    page = fetch(url)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_page_to_dict(page), ensure_ascii=False),
                    encoding="utf-8")
    return page


def _matches(result: dict, question: dict) -> bool:
    answer = result.get("answer", "")
    if question.get("expect_not_found"):
        return not result.get("citations") and "not found" in answer.lower()
    if not result.get("citations") or not result.get("verified"):
        return False
    lowered = normalize(answer)
    return any(normalize(value) in lowered
               for value in question.get("expect_any", []))


def run(questions: Sequence[dict], *, refresh: bool, offline: bool,
        answerer) -> dict:
    per_question = []
    citation_checked = 0
    citation_verified = 0
    pages_total = 0
    engines: Counter[str] = Counter()

    for question in questions:
        seen_pages: dict[str, Page] = {}

        def fetcher(url: str) -> Page:
            page = cached_fetch(url, refresh=refresh, offline=offline)
            seen_pages[page.url] = page
            seen_pages[page.final_url] = page
            return page

        agent = Agent(
            fetcher=fetcher,
            answerer=answerer,
            max_pages=question.get("max_pages", 1),
            max_depth=question.get("max_depth", 0),
        )
        result = agent.run(question["request"], question["start_urls"])
        pages = list({id(page): page for page in seen_pages.values()}.values())
        checked = verify_citations(result.get("citations", []), pages)
        citation_checked += len(result.get("citations", []))
        citation_verified += len(checked)
        pages_total += result.get("pages_read", 0)
        engines[result.get("engine", "unknown")] += 1
        passed = _matches(result, question)
        per_question.append({
            "id": question["id"],
            "request": question["request"],
            "start_urls": question["start_urls"],
            "expected": question.get("expect_any")
            or (["not found"] if question.get("expect_not_found") else []),
            "passed": passed,
            "answer": result.get("answer", ""),
            "citations": result.get("citations", []),
            "citations_found": result.get("citations_found", 0),
            "citations_dropped": result.get("citations_dropped", 0),
            "pages_read": result.get("pages_read", 0),
            "engine": result.get("engine", "unknown"),
            "verified": result.get("verified", False),
            **({"fallback_reason": result["fallback_reason"]}
               if "fallback_reason" in result else {}),
        })

    answerable = [q for q in per_question if q["expected"] != ["not found"]]
    not_found = [q for q in per_question if q["expected"] == ["not found"]]
    passed = sum(1 for q in per_question if q["passed"])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "eval/questions.json",
        "engine": dict(engines),
        "totals": {
            "questions": len(per_question),
            "passed": passed,
            "accuracy": round(passed / max(1, len(per_question)), 4),
            "answerable": len(answerable),
            "answerable_passed": sum(1 for q in answerable if q["passed"]),
            "not_found": len(not_found),
            "not_found_passed": sum(1 for q in not_found if q["passed"]),
            "citations_returned": citation_checked,
            "citations_verified": citation_verified,
            "citation_verify_rate": round(
                citation_verified / max(1, citation_checked), 4),
            "citations_dropped": sum(q["citations_dropped"]
                                     for q in per_question),
            "pages_read": pages_total,
        },
        "questions": per_question,
    }
    return report


def _print_table(report: dict) -> None:
    print(f"{'id':<16} {'pass':<5} {'engine':<20} {'pg':<3} "
          f"{'cit':<4} answer")
    for question in report["questions"]:
        answer = question["answer"].replace("\n", " ")
        if len(answer) > 58:
            answer = answer[:55] + "..."
        print(f"{question['id']:<16} {str(question['passed']):<5} "
              f"{question['engine']:<20} {question['pages_read']:<3} "
              f"{len(question['citations']):<4} {answer}")
    totals = report["totals"]
    print()
    print(f"accuracy {totals['passed']}/{totals['questions']} "
          f"({totals['accuracy']:.0%}) · "
          f"answerable {totals['answerable_passed']}/{totals['answerable']} · "
          f"not-found {totals['not_found_passed']}/{totals['not_found']}")
    print(f"citations verified {totals['citations_verified']}/"
          f"{totals['citations_returned']} "
          f"({totals['citation_verify_rate']:.0%}) · dropped "
          f"{totals['citations_dropped']} · pages {totals['pages_read']}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", default=str(ROOT / "questions.json"))
    parser.add_argument("--report", default=str(ROOT / "report.json"))
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--min-accuracy", type=float, default=0.8)
    args = parser.parse_args(argv)

    dataset = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    report = run(dataset["questions"], refresh=args.refresh,
                 offline=args.offline, answerer=build_answerer())
    Path(args.report).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    _print_table(report)
    print(f"\nreport: {args.report}")

    totals = report["totals"]
    if totals["citation_verify_rate"] < 1.0:
        print("FAIL: at least one returned citation did not verify", file=sys.stderr)
        return 1
    if totals["accuracy"] < args.min_accuracy:
        print(f"FAIL: accuracy {totals['accuracy']:.0%} below "
              f"{args.min_accuracy:.0%}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
