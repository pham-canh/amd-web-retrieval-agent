"""Verified web retrieval agent — AMD AI League, Match 4.

Pipeline: fetch (host-guarded) -> extract text -> chunk -> answer -> verify
citations. Every citation must be a verbatim quote from the fetched page; any
citation that cannot be verified is dropped.

The LLM path is optional. Without a key, a deterministic extractive answerer
runs and the output is labelled, so the demo never fakes a model call.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Callable, Iterable, Protocol, Sequence
from urllib.parse import urljoin, urlparse

MAX_BYTES = 2_000_000
MAX_BLOCK_CHARS = 700
MAX_UNIT_CHARS = 900
MIN_UNIT_CHARS = 20
MIN_ANSWER_SCORE = 0.34
DEFAULT_TIMEOUT = 15
USER_AGENT = "AMDLeagueRetrievalAgent/1.0 (+hackathon prototype)"

SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}
NOISY_TAGS = {"nav", "header", "footer", "aside", "form"}
BLOCK_TAGS = {
    "p", "div", "section", "article", "li", "tr", "br", "h1", "h2", "h3",
    "h4", "h5", "h6", "td", "th", "main", "nav", "aside", "header", "footer",
    "blockquote", "pre", "dt", "dd", "figcaption",
}
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}
NOISY_ROLES = {"navigation", "banner", "contentinfo", "complementary", "search"}
NOISY_ATTR_RE = re.compile(
    r"(?:^|[-_\s])("
    r"nav|navigation|menu|sidebar|footer|header|toc|catlinks?|printfooter|"
    r"mw-jump|interlanguage|vector-dropdown|aria-live|noprint|"
    r"metadata|navbox|reflist|references|mw-editsection|mw-cite|skip-link|"
    r"share|social|breadcrumb|cookie|banner|advert"
    r")(?:$|[-_\s])",
    re.IGNORECASE,
)
SKIP_EXTENSIONS = {
    ".7z", ".avi", ".bin", ".bmp", ".css", ".csv", ".doc", ".docx", ".eot",
    ".exe", ".gif", ".gz", ".ico", ".jpeg", ".jpg", ".js", ".json", ".m4a",
    ".mkv", ".mov", ".mp3", ".mp4", ".mpeg", ".pdf", ".png", ".ppt", ".pptx",
    ".rar", ".svg", ".tar", ".tif", ".tiff", ".ttf", ".wav", ".webm", ".webp",
    ".woff", ".woff2", ".xls", ".xlsx", ".xml", ".zip",
}
ALLOWED_CONTENT_TYPES = {
    "text/html", "application/xhtml+xml", "text/plain", "text/xml",
    "application/xml",
}
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on",
    "for", "and", "or", "what", "which", "who", "how", "when", "where", "why",
    "does", "do", "did", "with", "that", "this", "it", "at", "by", "from",
    "can", "could", "should", "would", "my", "your", "our", "their", "i",
    "be", "been", "being", "as", "its", "it's", "under", "about", "into",
    "over", "per", "between", "during", "without", "within",
}
INTENT_SYNONYMS = {
    "who": {"created", "designed", "developed", "conceived", "authored",
            "written", "founder", "invented", "built", "made"},
    "created": {"designed", "developed", "conceived", "authored", "written",
                "invented", "built", "made"},
    "create": {"created", "designed", "developed", "conceived", "invented"},
    "designed": {"created", "developed", "conceived", "authored", "written"},
    "developed": {"created", "designed", "conceived", "authored", "written"},
    "when": {"date", "year", "released", "launched", "founded", "published",
             "introduced", "born", "appeared"},
    "released": {"launched", "published", "introduced", "version", "date"},
    "launched": {"released", "published", "introduced", "date"},
    "founded": {"created", "established", "started", "date"},
    "where": {"located", "location", "based", "headquarters", "address",
              "country", "city"},
    "license": {"licensed", "licence", "licensing"},
    "port": {"tcp", "udp"},
    "serializes": {"dumps", "dump", "encode", "serialize"},
    "serialize": {"dumps", "dump", "encode", "serializes"},
    "deserializes": {"loads", "load", "decode", "parses", "parse"},
    "deserialize": {"loads", "load", "decode", "parses", "parse"},
    "mean": {"means", "meaning", "indicates", "defined", "description",
             "found", "stands"},
    "means": {"indicates", "defined", "description", "found", "stands"},
    "stand": {"stands", "notation", "abbreviation", "means", "represent"},
    "stands": {"notation", "abbreviation", "means", "represent"},
    "date": {"dated", "published", "released", "year", "january", "february",
             "march", "april", "may", "june", "july", "august", "september",
             "october", "november", "december"},
}
REFERENCE_MARK_RE = re.compile(
    r"\[\s*\d+\s*\]"
    r"|\[\s*(?:edit|citation needed|failed verification|update|show|hide|"
    r"note\s*\d+)\s*\]",
    re.IGNORECASE,
)


@dataclass
class Page:
    url: str
    final_url: str
    status: int
    html: str
    text: str
    blocks: tuple[str, ...] | None = None


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_stack: list[str] = []
        self._buffer: list[str] = []
        self._blocks: list[str] = []
        self._in_title = False
        self.title = ""

    @property
    def skipping(self) -> bool:
        return bool(self._skip_stack)

    def _is_noisy(self, tag: str, attrs) -> bool:
        if tag in SKIP_TAGS or tag in NOISY_TAGS:
            return True
        if tag in {"html", "body", "main", "article"}:
            return False
        for key, value in attrs:
            if not value:
                continue
            if key == "role" and value.lower() in NOISY_ROLES:
                return True
            if key == "aria-live":
                return True
            if key == "aria-hidden" and value.lower() == "true":
                return True
            if key in {"class", "id"} and NOISY_ATTR_RE.search(value):
                return True
        return False

    def _flush(self) -> None:
        block = _clean_block(" ".join(self._buffer))
        self._buffer = []
        if block:
            self._blocks.append(block)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "title":
            self._in_title = True
            return
        if self.skipping or self._is_noisy(tag, attrs):
            if tag not in VOID_TAGS:
                self._skip_stack.append(tag)
            return
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_startendtag(self, tag: str, attrs) -> None:
        if self.skipping:
            return
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            return
        if self.skipping:
            if tag in self._skip_stack:
                while self._skip_stack and self._skip_stack.pop() != tag:
                    pass
                if not self.skipping:
                    self._flush()
            return
        if tag in BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self.skipping:
            return
        if self._in_title:
            self.title += data
            return
        self._buffer.append(data)

    def blocks(self) -> list[str]:
        self._flush()
        return self._blocks


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag != "a":
            return
        for key, value in attrs:
            if key == "href" and value:
                self._href = value
                self._text = []
                return

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, _collapse(" ".join(self._text))))
            self._href = None
            self._text = []


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _clean_block(value: str) -> str:
    text = value.replace("\u200b", " ").replace("\xa0", " ")
    text = REFERENCE_MARK_RE.sub(" ", text)
    text = _collapse(text)
    if text.startswith(("•", "·", "|")):
        text = text.lstrip("•·| ").strip()
    return text


def normalize(value: str) -> str:
    return _collapse(value).lower()


def _query_terms(request: str) -> set[str]:
    terms: set[str] = set()
    for word in re.findall(r"[a-z0-9]+", normalize(request)):
        if len(word) < 2 or word in STOPWORDS:
            continue
        terms.add(word)
        terms |= INTENT_SYNONYMS.get(word, set())
    return terms


def relevant_excerpt(text: str, request: str, budget: int = 6000) -> str:
    """Pick query-relevant windows from a long page instead of its head.

    Long documents such as RFC 2616 keep the answer far past the first few
    thousand characters; scoring 1000-char windows by query-term overlap keeps
    the prompt small without hiding the relevant section.
    """
    if len(text) <= budget:
        return text
    terms = _query_terms(request)
    if not terms:
        return text[:budget]
    window, stride = 1000, 500
    lowered = text.lower()
    windows = [(start, lowered[start:start + window])
               for start in range(0, max(1, len(text) - window + 1), stride)]
    weight = {
        term: 1.0 + len(windows) / (1 + sum(1 for _, chunk in windows
                                           if term in chunk))
        for term in terms
    }
    scored: list[tuple[float, int]] = []
    for start, chunk in windows:
        score = sum(weight[term] for term in terms if term in chunk)
        if score:
            scored.append((score, start))
    if not scored:
        return text[:budget]
    scored.sort(key=lambda item: (-item[0], item[1]))
    chosen: list[int] = []
    for _, start in scored:
        if any(abs(start - other) < window for other in chosen):
            continue
        chosen.append(start)
        if len(chosen) * window >= budget:
            break
    chosen.sort()
    return "\n[...]\n".join(
        text[start:start + window] for start in chosen)[:budget]


def _split_long(text: str, limit: int = MAX_BLOCK_CHARS) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        while len(part) > limit:
            cut = part.rfind(" ", 0, limit)
            if cut <= 0:
                cut = limit
            if current:
                out.append(current)
                current = ""
            out.append(part[:cut].strip())
            part = part[cut:].strip()
        if current and len(current) + 1 + len(part) > limit:
            out.append(current)
            current = part
        else:
            current = f"{current} {part}".strip()
    if current:
        out.append(current)
    return [block for block in out if block]


def _dedupe(blocks: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for block in blocks:
        key = normalize(block)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(block)
    return out


def extract_blocks(html: str) -> list[str]:
    parser = _TextParser()
    parser.feed(html)
    parser.close()
    blocks: list[str] = []
    title = _clean_block(parser.title)
    if title:
        blocks.append(title)
    for block in parser.blocks():
        blocks.extend(_split_long(block))
    return _dedupe(blocks)


def extract_text(html: str) -> str:
    return _collapse(" ".join(extract_blocks(html)))


def _plain_blocks(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    raw: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = _collapse(paragraph)
        if paragraph:
            raw.extend(_split_long(paragraph))
    return _dedupe(raw)


def extract_links_with_text(html: str,
                            base_url: str) -> list[tuple[str, str]]:
    parser = _LinkParser()
    parser.feed(html)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for href, text in parser.links:
        if href.startswith(("mailto:", "javascript:", "#", "tel:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if _has_skipped_extension(parsed.path):
            continue
        url = absolute.split("#", 1)[0]
        if url in seen:
            continue
        seen.add(url)
        out.append((url, text))
    return out


def extract_links(html: str, base_url: str) -> list[str]:
    return [url for url, _ in extract_links_with_text(html, base_url)]


def _link_priority(url: str, text: str, terms: set[str]) -> float:
    if not terms:
        return 0.0
    text_terms = keywords(text)
    url_terms = keywords(url)
    overlap = len(terms & (text_terms | url_terms))
    return overlap / len(terms) + (0.2 if terms & url_terms else 0.0)


def _has_skipped_extension(path: str) -> bool:
    lowered = path.lower()
    return any(lowered.endswith(ext) for ext in SKIP_EXTENSIONS)


def _url_key(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}{query}"


def split_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\u201c])", text)
        if sentence.strip()
    ]


def keywords(value: str) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9]+", value.lower())
        if (len(word) > 2 or word.isdigit()) and word not in STOPWORDS
    }


def query_terms(request: str) -> tuple[set[str], set[str]]:
    base = keywords(request)
    bonus: set[str] = set()
    for word in re.findall(r"[a-z0-9]+", request.lower()):
        bonus |= INTENT_SYNONYMS.get(word, set())
    return base, bonus - base


def _intent_pattern(request: str) -> re.Pattern[str] | None:
    lowered = request.lower()
    if re.search(r"\b(who|whom|whose|created|create|designed|developed|"
                 r"conceived|authored|invented|founded)\b", lowered):
        return re.compile(
            r"\b(?:created|designed|developed|conceived|written|authored|"
            r"invented|founded|built)\b[^.]{0,40}?\bby\s+[A-Z]"
            r"|\bby\s+[A-Z][^.]{0,40}?\b(?:created|designed|developed|"
            r"conceived|written|authored|invented|founded)\b"
            r"|^[A-Z][\w'’-]+(?:\s+[A-Z][\w'’-]+){0,3}\s+(?:created|designed|"
            r"developed|conceived|wrote|authored|invented|founded)\b")
    if re.search(r"^\s*when\b|\bwhen\s+(?:was|were|did|is|does|do)\b|"
                 r"\bdate\b|\bdated\b", lowered):
        return re.compile(
            r"\b(?:1[89]\d{2}|20\d{2})\b|\b(?:January|February|March|April|"
            r"May|June|July|August|September|October|November|December)\b",
            re.IGNORECASE)
    if re.search(r"\bhow many\b|\bnumber\b|\bcount\b|\btotal\b", lowered):
        return re.compile(r"\b\d[\d,.]*\b")
    if re.search(r"\b(where|located|location|headquarters)\b", lowered):
        return re.compile(r"\b(?:located|based|headquarters|in|at)\b",
                          re.IGNORECASE)
    if re.search(r"\b(mean|meaning|means|stand for)\b", lowered):
        return re.compile(r"\b(?:means|indicates|defined|description|found)\b",
                          re.IGNORECASE)
    return None


def _required_pattern(request: str) -> re.Pattern[str] | None:
    """A shape the answer sentence must have, when the question implies one."""
    lowered = request.lower()
    if re.search(r"\b(who|whom|whose|created|create|designed|developed|"
                 r"conceived|authored|invented|founded)\b", lowered):
        return re.compile(
            r"\b(?:created|designed|developed|conceived|written|authored|"
            r"invented|founded|built)\b[^.]{0,40}?\bby\s+[A-Z]"
            r"|\bby\s+[A-Z][^.]{0,40}?\b(?:created|designed|developed|"
            r"conceived|written|authored|invented|founded)\b"
            r"|^[A-Z][\w'’-]+(?:\s+[A-Z][\w'’-]+){0,3}\s+(?:created|designed|"
            r"developed|conceived|wrote|authored|invented|founded)\b")
    if re.search(r"^\s*when\b|\bwhen\s+(?:was|were|did|is|does|do)\b|"
                 r"\bdate\b|\bdated\b", lowered):
        return re.compile(
            r"\b(?:1[89]\d{2}|20\d{2})\b|\b(?:January|February|March|April|"
            r"May|June|July|August|September|October|November|December)\b",
            re.IGNORECASE)
    if re.search(r"\blicen[cs]e\b|\blicensed\b|\blicenced\b", lowered):
        return re.compile(r"\blicen[cs]e\b", re.IGNORECASE)
    if re.search(r"\bexception\b|\berror\b", lowered):
        return re.compile(r"\b\w*(?:Error|Exception)\b")
    if re.search(r"\bwhich function\b|\bwhat function\b", lowered):
        return re.compile(
            r"\b(?:dumps|dump|loads|load|detect_encoding|encode|decode)\b",
            re.IGNORECASE)
    if re.search(r"\bport\b", lowered):
        return re.compile(r"\bport\b", re.IGNORECASE)
    if re.search(r"\bmean|meaning\b", lowered):
        return re.compile(r"\b(?:means|indicates|defined|description|found)\b",
                          re.IGNORECASE)
    return None


def _meta_charset(raw: bytes) -> str | None:
    head = raw[:4096].decode("latin-1", errors="ignore")
    match = re.search(r"charset\s*=\s*[\"']?([\w-]+)", head, re.IGNORECASE)
    return match.group(1) if match else None


def fetch(url: str, timeout: int = DEFAULT_TIMEOUT) -> Page:
    if urlparse(url).scheme not in {"http", "https"}:
        raise ValueError(f"unsupported scheme: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_BYTES)
        status = getattr(response, "status", 0)
        final_url = response.geturl()
        content_type = response.headers.get_content_type()
        charset = response.headers.get_content_charset() or _meta_charset(raw)
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"unsupported content-type: {content_type}")
    html = raw.decode(charset or "utf-8", errors="replace")
    if content_type in {"text/plain", "text/xml", "application/xml"}:
        blocks = _plain_blocks(html)
    else:
        blocks = extract_blocks(html)
    text = _collapse(" ".join(blocks))
    return Page(url=url, final_url=final_url, status=status, html=html,
                text=text, blocks=tuple(blocks))


def crawl(
    start_urls: Sequence[str],
    *,
    fetcher: Callable[[str], Page] = fetch,
    max_pages: int = 3,
    max_depth: int = 1,
    request: str | None = None,
    trace: list[dict] | None = None,
) -> list[Page]:
    allowed = {urlparse(url).netloc.lower() for url in start_urls}
    terms = keywords(request) if request else set()
    seen: set[str] = set()
    pages: list[Page] = []
    steps = trace if trace is not None else []
    queue: list[tuple[float, str, int]] = [
        (float("inf"), url, 0) for url in start_urls
    ]
    while queue and len(pages) < max_pages:
        queue.sort(key=lambda row: row[0], reverse=True)
        priority, url, depth = queue.pop(0)
        key = _url_key(url)
        if key in seen or urlparse(url).netloc.lower() not in allowed:
            continue
        if _has_skipped_extension(urlparse(url).path):
            continue
        seen.add(key)
        try:
            page = fetcher(url)
        except (urllib.error.URLError, ValueError, OSError, UnicodeError) as exc:
            steps.append({
                "url": url,
                "depth": depth,
                "outcome": "failed",
                "error": type(exc).__name__,
            })
            continue
        queued = 0
        if depth < max_depth and \
                urlparse(page.final_url).netloc.lower() in allowed:
            for link, text in extract_links_with_text(page.html,
                                                      page.final_url):
                if _url_key(link) not in seen:
                    link_score = _link_priority(link, text, terms)
                    queue.append((link_score, link, depth + 1))
                    queued += 1
        pages.append(page)
        steps.append({
            "url": url,
            "final_url": page.final_url,
            "depth": depth,
            "outcome": "read",
            "chars": len(page.text),
            "links_queued": queued,
            **({"link_score": round(priority, 3)}
               if priority != float("inf") else {}),
        })
    return pages


class Answerer(Protocol):
    name: str

    def answer(self, request: str, pages: Sequence[Page]) -> dict: ...


def _units(page: Page) -> Iterable[str]:
    blocks = page.blocks or (page.text,)
    for block in blocks:
        for sentence in split_sentences(block):
            sentence = sentence.strip()
            if MIN_UNIT_CHARS <= len(sentence) <= MAX_UNIT_CHARS:
                yield sentence


def _code_ratio(value: str) -> float:
    if not value:
        return 0.0
    symbols = sum(value.count(ch) for ch in "{}[]=<>|\\`~")
    return symbols / len(value)


def _comma_ratio(value: str) -> float:
    return value.count(",") / len(value) if value else 0.0


def _score_unit(
    sentence: str,
    base: set[str],
    bonus: set[str],
    intent: re.Pattern[str] | None,
) -> tuple[float, int]:
    unit_terms = keywords(sentence)
    overlap = len(base & unit_terms)
    extra = len(bonus & unit_terms)
    if overlap == 0:
        return 0.0, 0
    score = (overlap + 1.0 * extra) / max(1, len(base))
    if intent is not None and intent.search(sentence):
        score += 0.4
    if len(sentence) > 500:
        score -= 0.3
    if _code_ratio(sentence) > 0.04:
        score -= 0.4
    if _comma_ratio(sentence) > 0.08:
        score -= 0.2
    return score, overlap


class ExtractiveAnswerer:
    """Deterministic fallback: keyword overlap over page sentences."""

    name = "extractive-fallback"

    def _rank(
        self,
        pages: Sequence[Page],
        base: set[str],
        bonus: set[str],
        intent: re.Pattern[str] | None,
        required: re.Pattern[str] | None,
    ) -> dict[str, tuple[float, str, int]]:
        best_by_url: dict[str, tuple[float, str, int]] = {}
        for page in pages:
            for sentence in _units(page):
                if required is not None and not required.search(sentence):
                    continue
                score, overlap = _score_unit(sentence, base, bonus, intent)
                if score <= 0:
                    continue
                previous = best_by_url.get(page.final_url)
                if previous is None or (score, overlap) > (previous[0],
                                                           previous[2]):
                    best_by_url[page.final_url] = (score, sentence, overlap)
        return best_by_url

    def answer(self, request: str, pages: Sequence[Page]) -> dict:
        base, bonus = query_terms(request)
        intent = _intent_pattern(request)
        required = _required_pattern(request)
        best_by_url = self._rank(pages, base, bonus, intent, required)
        if not best_by_url and required is not None:
            best_by_url = self._rank(pages, base, bonus, intent, None)
        if not best_by_url:
            return {
                "answer": "Not found on the pages read.",
                "citations": [],
                "engine": self.name,
            }
        ranked = sorted(best_by_url.items(),
                        key=lambda row: (row[1][0], row[1][2]), reverse=True)
        top_score = ranked[0][1][0]
        if top_score < MIN_ANSWER_SCORE:
            return {
                "answer": "Not found on the pages read.",
                "citations": [],
                "engine": self.name,
            }
        threshold = max(MIN_ANSWER_SCORE, 0.7 * top_score)
        selected = [
            (url, sentence)
            for url, (score, sentence, _) in ranked[:2]
            if score >= threshold
        ]
        citations = [{"url": url, "quote": quote} for url, quote in selected]
        return {
            "answer": " ".join(quote for _, quote in selected),
            "citations": citations,
            "engine": self.name,
        }


class OpenAICompatibleAnswerer:
    """Minimal chat-completions client; expects a JSON object back."""

    name = "llm"

    def __init__(self, base_url: str, api_key: str, model: str,
                 timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _prompt(self, request: str, pages: Sequence[Page]) -> str:
        blocks = []
        for index, page in enumerate(pages, 1):
            excerpt = relevant_excerpt(page.text, request, 6000)
            blocks.append(f"[{index}] {page.final_url}\n{excerpt}")
        return (
            "Answer the user's request using ONLY the page excerpts below. Be "
            "concise: one short sentence. Return a JSON object with keys "
            '"answer" and "citations". Include exactly one citation when the '
            'answer is present: {"url": <page url>, "quote": <text copied '
            "character-for-character from that page excerpt, with no ellipses "
            "and no paraphrase>}. The quote must appear verbatim in the "
            "excerpt. If the answer is absent, return answer 'Not found on the "
            "pages read' with an empty citations list.\n\n"
            f"Request: {request}\n\n" + "\n\n".join(blocks)
        )

    def _post(self, data: bytes, attempts: int = 3) -> dict:
        """POST once, retrying the transient failures Token Lab documents."""
        for attempt in range(attempts):
            request_obj = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(
                        request_obj, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504} or attempt == attempts - 1:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == attempts - 1:
                    raise
            time.sleep(2 * (attempt + 1))
        raise RuntimeError("unreachable")

    def answer(self, request: str, pages: Sequence[Page]) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You extract facts with citations."},
                {"role": "user", "content": self._prompt(request, pages)},
            ],
            "temperature": 0,
            "max_tokens": 800,
            "response_format": {"type": "json_object"},
        }
        body = self._post(json.dumps(payload).encode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start < 0 or end <= start:
                raise
            parsed = json.loads(content[start:end + 1])
        return {
            "answer": parsed.get("answer", ""),
            "citations": parsed.get("citations", []),
            "engine": self.name,
        }


def verify_citations(citations: Iterable[dict], pages: Sequence[Page]) -> list[dict]:
    corpus: dict[str, str] = {}
    for page in pages:
        haystack = normalize(page.text)
        corpus[page.url] = haystack
        corpus[page.final_url] = haystack
        corpus[_url_key(page.url)] = haystack
        corpus[_url_key(page.final_url)] = haystack
    verified: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for citation in citations:
        url = citation.get("url", "")
        quote = citation.get("quote", "")
        haystack = corpus.get(url) or corpus.get(_url_key(url))
        if haystack is None or not quote:
            continue
        if normalize(quote) not in haystack:
            continue
        key = (url, normalize(quote))
        if key in seen:
            continue
        seen.add(key)
        verified.append({"url": url, "quote": quote})
    return verified


def build_answerer() -> Answerer:
    base_url = os.environ.get("LLM_BASE_URL")
    api_key = os.environ.get("LLM_API_KEY")
    model = os.environ.get("LLM_MODEL")
    if base_url and api_key and model:
        return OpenAICompatibleAnswerer(base_url, api_key, model)
    return ExtractiveAnswerer()


class Agent:
    def __init__(
        self,
        *,
        fetcher: Callable[[str], Page] = fetch,
        answerer: Answerer | None = None,
        max_pages: int = 3,
        max_depth: int = 1,
    ) -> None:
        self.fetcher = fetcher
        self.answerer = answerer or build_answerer()
        self.max_pages = max_pages
        self.max_depth = max_depth

    def run(self, request: str, start_urls: Sequence[str]) -> dict:
        steps: list[dict] = []
        pages = crawl(
            start_urls,
            fetcher=self.fetcher,
            max_pages=self.max_pages,
            max_depth=self.max_depth,
            request=request,
            trace=steps,
        )
        if not pages:
            return {
                "request": request,
                "answer": "No pages could be read.",
                "citations": [],
                "citations_found": 0,
                "citations_dropped": 0,
                "pages_read": 0,
                "engine": self.answerer.name,
                "verified": True,
                "steps": steps,
                "pages": [],
            }
        try:
            result = self.answerer.answer(request, pages)
        except Exception as exc:  # keep the demo alive, never fake a model call
            fallback = ExtractiveAnswerer()
            result = fallback.answer(request, pages)
            result["engine"] = fallback.name
            result["fallback_reason"] = type(exc).__name__
        raw_citations = result.get("citations", [])
        citations = verify_citations(raw_citations, pages)
        if (result.get("engine") == "llm" and not citations
                and "not found" not in result.get("answer", "").lower()):
            fallback = ExtractiveAnswerer()
            alt = fallback.answer(request, pages)
            alt_citations = verify_citations(alt.get("citations", []), pages)
            if alt_citations:
                alt["engine"] = fallback.name
                alt["fallback_reason"] = "unverified-llm-citation"
                result = alt
                raw_citations = alt.get("citations", [])
                citations = alt_citations
        return {
            "request": request,
            "answer": result.get("answer", ""),
            "citations": citations,
            "citations_found": len(raw_citations),
            "citations_dropped": len(raw_citations) - len(citations),
            "pages_read": len(pages),
            "engine": result.get("engine", self.answerer.name),
            "verified": len(citations) == len(raw_citations),
            "steps": steps,
            "pages": [
                {"url": page.url, "final_url": page.final_url,
                 "chars": len(page.text)}
                for page in pages
            ],
            **({"fallback_reason": result["fallback_reason"]}
               if "fallback_reason" in result else {}),
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--start", action="append", required=True,
                        help="starting URL (repeatable)")
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--max-depth", type=int, default=1)
    parser.add_argument("--out", help="also write the JSON result to this path")
    args = parser.parse_args(argv)

    agent = Agent(max_pages=args.max_pages, max_depth=args.max_depth)
    result = agent.run(args.request, args.start)
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    sys.stdout.write(rendered + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
