"""OG & Twitter Metadata checker (#21) — discovers social sharing metadata.

Finds and extracts all Open Graph and Twitter Card meta tags, reports
what's present, what's missing, and their actual values.
"""
from __future__ import annotations

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult

# Tags to discover and their point weight (for deriving a score)
OG_TAGS = [
    ("og:title", 15),
    ("og:description", 15),
    ("og:image", 10),
    ("og:url", 10),
    ("og:type", 5),
    ("og:site_name", 5),
]

TWITTER_TAGS = [
    ("twitter:card", 10),
    ("twitter:title", 10),
    ("twitter:image", 5),
    ("twitter:description", 5),
]


class OgMetadataChecker(BaseChecker):
    check_id = "og_metadata"
    check_number = 21
    name = "OG & Twitter Metadata"
    layer = Layer.NODE_READABILITY

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        details: dict = {"og": {}, "twitter": {}}
        score = 0.0

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        soup = crawl.soup

        def _get_meta(property_name: str) -> str | None:
            tag = soup.find("meta", property=property_name)
            if tag and tag.get("content", "").strip():
                return tag["content"].strip()
            tag = soup.find("meta", attrs={"name": property_name})
            if tag and tag.get("content", "").strip():
                return tag["content"].strip()
            return None

        # ── Discover Open Graph tags ───────────────────────────────────
        og_found: list[str] = []
        og_missing: list[str] = []
        for tag_name, weight in OG_TAGS:
            value = _get_meta(tag_name)
            short = tag_name.split(":")[1]  # "title", "description", etc.
            if value:
                og_found.append(tag_name)
                details["og"][short] = value[:200]
                findings.append(f"og_{short}_found")
                score += weight
            else:
                og_missing.append(tag_name)
                findings.append(f"og_{short}_missing")

        # ── Discover Twitter Card tags ─────────────────────────────────
        tw_found: list[str] = []
        tw_missing: list[str] = []
        for tag_name, weight in TWITTER_TAGS:
            value = _get_meta(tag_name)
            short = tag_name.split(":")[1]
            if value:
                tw_found.append(tag_name)
                details["twitter"][short] = value[:200]
                findings.append(f"twitter_{short}_found")
                score += weight
            else:
                tw_missing.append(tag_name)
                findings.append(f"twitter_{short}_missing")

        # ── Quality details ────────────────────────────────────────────
        # Image dimensions
        og_width = _get_meta("og:image:width")
        og_height = _get_meta("og:image:height")
        if og_width and og_height:
            details["og"]["image_dimensions"] = f"{og_width}x{og_height}"
            findings.append(f"og_image_dimensions:{og_width}x{og_height}")
            score += 5
        elif details["og"].get("image"):
            findings.append("og_image_no_dimensions")

        # Description length
        og_desc = details["og"].get("description", "")
        if og_desc:
            desc_len = len(og_desc)
            details["og"]["description_length"] = desc_len
            findings.append(f"og_description_length:{desc_len}")
            if 50 <= desc_len <= 160:
                score += 5

        # Summary
        details["og_tags_found"] = len(og_found)
        details["og_tags_missing"] = og_missing
        details["twitter_tags_found"] = len(tw_found)
        details["twitter_tags_missing"] = tw_missing

        return self._make_result(score, findings, details)
