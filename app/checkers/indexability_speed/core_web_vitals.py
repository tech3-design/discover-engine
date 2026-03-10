from __future__ import annotations

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult


class CoreWebVitalsChecker(BaseChecker):
    check_id = "core_web_vitals"
    check_number = 10
    name = "Core Web Vitals & Load Time"
    layer = Layer.INDEXABILITY_SPEED

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        score = 0.0

        # Load time scoring
        load_s = crawl.load_time_ms / 1000
        if load_s < 1.5:
            score += 70
            findings.append(f"fast_load_time:{load_s:.1f}s")
        elif load_s < 3:
            score += 50
            findings.append(f"moderate_load_time:{load_s:.1f}s")
        elif load_s < 5:
            score += 25
            findings.append(f"slow_load_time:{load_s:.1f}s")
        else:
            findings.append(f"very_slow_load_time:{load_s:.1f}s")

        # Viewport meta tag
        if crawl.soup:
            viewport = crawl.soup.find("meta", attrs={"name": "viewport"})
            if viewport:
                score += 15
                findings.append("viewport_meta_present")
            else:
                findings.append("viewport_meta_missing")

            # Check for resource hints (preconnect, preload)
            preconnect = crawl.soup.find_all("link", rel="preconnect")
            preload = crawl.soup.find_all("link", rel="preload")
            if preconnect or preload:
                score += 15
                findings.append("resource_hints_present")
            else:
                findings.append("no_resource_hints")
        else:
            findings.append("no_html")

        return self._make_result(score, findings, {"load_time_ms": crawl.load_time_ms})
