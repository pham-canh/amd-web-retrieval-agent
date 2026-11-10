from __future__ import annotations

import json
import unittest
import urllib.error
from unittest import mock

from web_retrieval_agent import (
    Agent,
    ExtractiveAnswerer,
    OpenAICompatibleAnswerer,
    Page,
    _link_priority,
    _meta_charset,
    crawl,
    extract_blocks,
    extract_text,
    relevant_excerpt,
    verify_citations,
)

SITE = {
    "https://clinic.test/pricing": """
        <html><head><title>Pricing</title>
        <style>.x{color:red}</style></head>
        <body>
          <nav>Home Pricing Contact</nav>
          <h1>Plans</h1>
          <p>Annual plans can be refunded within 30 days of purchase.</p>
          <p>Monthly plans are billed at $29 per clinic.</p>
          <script>var tracking = "should not appear";</script>
          <a href="/refunds">Refund policy</a>
        </body></html>
    """,
    "https://clinic.test/refunds": """
        <html><body>
          <p>Refunds are processed within five business days.</p>
        </body></html>
    """,
}


def fake_fetch(url: str) -> Page:
    if url not in SITE:
        raise ValueError(f"unexpected url: {url}")
    html = SITE[url]
    return Page(url=url, final_url=url, status=200, html=html,
                text=extract_text(html))


class TextExtractionTests(unittest.TestCase):
    def test_drops_script_and_style(self) -> None:
        text = extract_text(SITE["https://clinic.test/pricing"])
        self.assertIn("refunded within 30 days", text)
        self.assertNotIn("should not appear", text)
        self.assertNotIn("color:red", text)

    def test_collapses_whitespace(self) -> None:
        text = extract_text("<p>a\n\n   b</p>")
        self.assertEqual(text, "a b")


class NoiseTests(unittest.TestCase):
    def test_drops_navigation_categories_and_live_regions(self) -> None:
        html = """
            <html><body>
              <nav>Home Pricing Contact</nav>
              <div class="catlinks">Categories: A B C</div>
              <div aria-live="polite">Jump to content</div>
              <main><p>Annual plans can be refunded within 30 days.</p></main>
              <footer>Copyright notice</footer>
            </body></html>
        """
        text = extract_text(html)
        self.assertIn("refunded within 30 days", text)
        self.assertNotIn("Home Pricing Contact", text)
        self.assertNotIn("Categories", text)
        self.assertNotIn("Jump to content", text)
        self.assertNotIn("Copyright notice", text)

    def test_blocks_split_on_block_boundaries(self) -> None:
        blocks = extract_blocks("<p>first fact.</p><p>second fact.</p>")
        self.assertIn("first fact.", blocks)
        self.assertIn("second fact.", blocks)

    def test_meta_charset_is_detected(self) -> None:
        raw = b'<meta charset="iso-8859-1"><p>caf\xe9</p>'
        self.assertEqual(_meta_charset(raw), "iso-8859-1")
        self.assertIsNone(_meta_charset(b"<p>no charset</p>"))


class LinkPriorityTests(unittest.TestCase):
    def test_prefers_relevant_anchor_text(self) -> None:
        terms = {"pickle"}
        relevant = _link_priority("https://docs.test/pickle.html",
                                  "pickle module", terms)
        noisy = _link_priority("https://docs.test/contents.html",
                               "Contents", terms)
        self.assertGreater(relevant, noisy)

    def test_crawl_skips_binary_links(self) -> None:
        html = '<a href="/manual.pdf">manual</a>'
        page = Page(url="https://clinic.test/a",
                    final_url="https://clinic.test/a",
                    status=200, html=html, text=extract_text(html))
        pages = crawl(["https://clinic.test/a"],
                      fetcher=lambda url: page, max_pages=3, max_depth=1)
        self.assertEqual(len(pages), 1)


class CitationTests(unittest.TestCase):
    def test_keeps_verbatim_quote(self) -> None:
        pages = [fake_fetch("https://clinic.test/pricing")]
        citations = [{"url": pages[0].final_url,
                      "quote": "Annual plans can be refunded within 30 days of purchase."}]
        self.assertEqual(len(verify_citations(citations, pages)), 1)

    def test_drops_invented_quote(self) -> None:
        pages = [fake_fetch("https://clinic.test/pricing")]
        citations = [{"url": pages[0].final_url,
                      "quote": "Annual plans can be refunded within 90 days."}]
        self.assertEqual(verify_citations(citations, pages), [])

    def test_drops_unknown_url(self) -> None:
        pages = [fake_fetch("https://clinic.test/pricing")]
        citations = [{"url": "https://other.test/", "quote": "anything"}]
        self.assertEqual(verify_citations(citations, pages), [])

    def test_accepts_redirect_final_url(self) -> None:
        html = "<p>Annual plans can be refunded within 30 days.</p>"
        page = Page(url="https://clinic.test/old",
                    final_url="https://clinic.test/new",
                    status=200, html=html, text=extract_text(html))
        quote = "Annual plans can be refunded within 30 days."
        citations = [
            {"url": "https://clinic.test/new", "quote": quote},
            {"url": "https://clinic.test/old", "quote": quote},
        ]
        verified = verify_citations(citations, [page])
        self.assertEqual(len(verified), 2)
        self.assertEqual({item["url"] for item in verified},
                         {"https://clinic.test/new", "https://clinic.test/old"})


class CrawlTests(unittest.TestCase):
    def test_follows_same_host_link(self) -> None:
        pages = crawl(["https://clinic.test/pricing"], fetcher=fake_fetch,
                      max_pages=3, max_depth=1)
        urls = {page.final_url for page in pages}
        self.assertIn("https://clinic.test/refunds", urls)

    def test_refuses_foreign_host(self) -> None:
        def guarded(url: str) -> Page:
            if "clinic.test" not in url:
                raise AssertionError(f"fetched foreign host: {url}")
            return fake_fetch(url)

        html = '<a href="https://evil.test/x">x</a>'
        page = Page(url="https://clinic.test/a", final_url="https://clinic.test/a",
                    status=200, html=html, text=extract_text(html))
        pages = crawl(["https://clinic.test/a"],
                      fetcher=lambda url: page if url.endswith("/a") else guarded(url),
                      max_pages=3, max_depth=1)
        self.assertEqual(len(pages), 1)

    def test_trace_records_navigation(self) -> None:
        trace: list[dict] = []
        crawl(["https://clinic.test/pricing"], fetcher=fake_fetch,
              max_pages=3, max_depth=1, request="refund policy", trace=trace)
        urls = [step["url"] for step in trace]
        self.assertEqual(urls[0], "https://clinic.test/pricing")
        self.assertIn("https://clinic.test/refunds", urls)
        first = trace[0]
        self.assertEqual(first["depth"], 0)
        self.assertEqual(first["outcome"], "read")
        self.assertGreater(first["chars"], 0)
        self.assertGreater(first["links_queued"], 0)
        follower = next(s for s in trace if s["url"].endswith("/refunds"))
        self.assertEqual(follower["depth"], 1)
        self.assertIn("link_score", follower)

    def test_trace_records_fetch_failure(self) -> None:
        def broken(url: str) -> Page:
            raise ValueError("offline")

        trace: list[dict] = []
        crawl(["https://clinic.test/x"], fetcher=broken, trace=trace)
        self.assertEqual(trace[0]["outcome"], "failed")
        self.assertEqual(trace[0]["error"], "ValueError")


class AgentTests(unittest.TestCase):
    def test_answers_with_verified_citation(self) -> None:
        agent = Agent(fetcher=fake_fetch, answerer=ExtractiveAnswerer(),
                      max_pages=1, max_depth=0)
        result = agent.run("What is the refund window for annual plans?",
                           ["https://clinic.test/pricing"])
        self.assertEqual(result["engine"], "extractive-fallback")
        self.assertTrue(result["verified"])
        self.assertGreaterEqual(len(result["citations"]), 1)
        self.assertIn("30 days", result["answer"])

    def test_returns_not_found_without_match(self) -> None:
        agent = Agent(fetcher=fake_fetch, answerer=ExtractiveAnswerer(),
                      max_pages=1, max_depth=0)
        result = agent.run("What is the parking policy?",
                           ["https://clinic.test/pricing"])
        self.assertEqual(result["citations"], [])
        self.assertIn("Not found", result["answer"])

    def test_no_pages_read(self) -> None:
        def broken(url: str) -> Page:
            raise ValueError("offline")

        agent = Agent(fetcher=broken, answerer=ExtractiveAnswerer())
        result = agent.run("anything", ["https://clinic.test/pricing"])
        self.assertEqual(result["pages_read"], 0)
        self.assertIn("No pages", result["answer"])

    def test_output_is_json_serialisable(self) -> None:
        agent = Agent(fetcher=fake_fetch, answerer=ExtractiveAnswerer(),
                      max_pages=2, max_depth=1)
        result = agent.run("How long do refunds take?",
                           ["https://clinic.test/refunds"])
        json.dumps(result)

    def test_answers_from_linked_page(self) -> None:
        pages = {
            "https://clinic.test/start": """
                <p>Welcome to the clinic.</p>
                <a href="/details">Pickle storage details</a>
            """,
            "https://clinic.test/details": """
                <p>Pickle storage keeps samples cold for 30 days.</p>
            """,
        }

        def linked_fetch(url: str) -> Page:
            html = pages[url]
            return Page(url=url, final_url=url, status=200, html=html,
                        text=extract_text(html))

        agent = Agent(fetcher=linked_fetch, answerer=ExtractiveAnswerer(),
                      max_pages=2, max_depth=1)
        result = agent.run("How long does pickle storage keep samples cold?",
                           ["https://clinic.test/start"])
        self.assertEqual(result["pages_read"], 2)
        self.assertEqual(result["citations"][0]["url"],
                         "https://clinic.test/details")
        self.assertIn("30 days", result["answer"])

    def test_falls_back_when_llm_raises(self) -> None:
        class BrokenAnswerer:
            name = "llm"

            def answer(self, request, pages):
                raise RuntimeError("quota exhausted")

        agent = Agent(fetcher=fake_fetch, answerer=BrokenAnswerer(),
                      max_pages=1, max_depth=0)
        result = agent.run("What is the refund window for annual plans?",
                           ["https://clinic.test/pricing"])
        self.assertEqual(result["engine"], "extractive-fallback")
        self.assertEqual(result["fallback_reason"], "RuntimeError")
        self.assertTrue(result["verified"])
        self.assertIn("30 days", result["answer"])


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args) -> bool:
        return False


class LlmAnswererTests(unittest.TestCase):
    def test_parses_json_and_strips_code_fence(self) -> None:
        content = json.dumps({
            "answer": "Annual plans can be refunded within 30 days.",
            "citations": [{
                "url": "https://clinic.test/pricing",
                "quote": "Annual plans can be refunded within 30 days.",
            }],
        })
        body = json.dumps({
            "choices": [{"message": {"content": f"```json\n{content}\n```"}}],
        }).encode()
        answerer = OpenAICompatibleAnswerer("https://llm.test/v1", "key",
                                             "model")
        with mock.patch("web_retrieval_agent.urllib.request.urlopen",
                        return_value=FakeResponse(body)):
            result = answerer.answer("refund window",
                                     [fake_fetch("https://clinic.test/pricing")])
        self.assertEqual(result["engine"], "llm")
        self.assertEqual(result["answer"],
                         "Annual plans can be refunded within 30 days.")
        self.assertEqual(len(result["citations"]), 1)

    def test_retries_transient_5xx(self) -> None:
        body = json.dumps({
            "choices": [{"message": {"content": json.dumps({
                "answer": "ok", "citations": [],
            })}}],
        }).encode()
        error = urllib.error.HTTPError("https://llm.test/v1", 503, "busy",
                                       None, None)
        answerer = OpenAICompatibleAnswerer("https://llm.test/v1", "key",
                                             "model")
        with mock.patch("web_retrieval_agent.urllib.request.urlopen",
                        side_effect=[error, FakeResponse(body)]) as post, \
                mock.patch("web_retrieval_agent.time.sleep"):
            result = answerer.answer("q", [])
        self.assertEqual(result["answer"], "ok")
        self.assertEqual(post.call_count, 2)


class ExcerptTests(unittest.TestCase):
    def test_keeps_late_section_of_long_page(self) -> None:
        text = ("filler " * 8000) + " The default port for HTTP is 80. " + \
            ("tail " * 8000)
        excerpt = relevant_excerpt(
            text, "What is the default port for the HTTP protocol?")
        self.assertIn("default port for HTTP is 80", excerpt)
        self.assertLessEqual(len(excerpt), 6000)


if __name__ == "__main__":
    unittest.main()
