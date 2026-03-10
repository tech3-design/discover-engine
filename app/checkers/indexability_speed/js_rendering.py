from __future__ import annotations

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult
from app.utils.html_helpers import count_words


class JsRenderingChecker(BaseChecker):
    check_id = "js_rendering"
    check_number = 11
    name = "JS Rendering Visibility"
    layer = Layer.INDEXABILITY_SPEED

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        score = 0.0

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        # Check for noscript fallback
        noscript = crawl.soup.find_all("noscript")
        if noscript:
            score += 25
            findings.append("noscript_fallback_present")
        else:
            findings.append("no_noscript_fallback")

        # Check main content presence in raw HTML
        main_tag = crawl.soup.find("main") or crawl.soup.find("article")
        if main_tag:
            score += 25
            findings.append("main_content_in_html")
        else:
            findings.append("no_main_content_element")

        # Word count in raw HTML — if very low, likely JS-rendered
        word_count = count_words(crawl.text)
        if word_count >= 200:
            score += 30
            findings.append(f"sufficient_html_text:{word_count}_words")
        elif word_count >= 50:
            score += 15
            findings.append(f"minimal_html_text:{word_count}_words")
        else:
            findings.append(f"very_low_html_text:{word_count}_words")

        # Check for SSR indicators
        root_div = crawl.soup.find("div", id="__next") or crawl.soup.find("div", id="root") or crawl.soup.find("div", id="app")
        if root_div and root_div.get_text(strip=True):
            score += 20
            findings.append("ssr_content_detected")
        elif root_div:
            findings.append("empty_root_div_csr_likely")

        return self._make_result(score, findings, {"word_count": word_count})
