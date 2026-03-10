from __future__ import annotations

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult


class InternalLinkingChecker(BaseChecker):
    check_id = "internal_linking"
    check_number = 12
    name = "Internal Linking Structure"
    layer = Layer.GRAPH_DISCOVERY

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        score = 0.0

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        link_count = len(crawl.internal_links)
        findings.append(f"internal_links_count:{link_count}")

        # Link count scoring
        if link_count >= 10:
            score += 40
            findings.append("excellent_link_count")
        elif link_count >= 5:
            score += 30
            findings.append("good_link_count")
        elif link_count >= 3:
            score += 20
            findings.append("adequate_link_count")
        else:
            findings.append("insufficient_links")

        # Anchor text diversity
        anchors = []
        for a in crawl.soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if text:
                anchors.append(text.lower())

        if anchors:
            unique_ratio = len(set(anchors)) / len(anchors)
            if unique_ratio >= 0.7:
                score += 30
                findings.append("diverse_anchor_text")
            elif unique_ratio >= 0.4:
                score += 15
                findings.append("moderate_anchor_diversity")
            else:
                findings.append("low_anchor_diversity")

        # Nav + contextual links
        nav = crawl.soup.find("nav")
        if nav:
            nav_links = nav.find_all("a", href=True)
            score += 15
            findings.append(f"nav_links:{len(nav_links)}")

        # Contextual links (links within paragraphs)
        contextual = 0
        for p in crawl.soup.find_all("p"):
            contextual += len(p.find_all("a", href=True))
        if contextual >= 3:
            score += 15
            findings.append(f"contextual_links:{contextual}")
        elif contextual >= 1:
            score += 8
            findings.append(f"few_contextual_links:{contextual}")

        return self._make_result(score, findings, {"link_count": link_count})
