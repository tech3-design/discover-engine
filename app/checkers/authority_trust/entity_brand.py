from __future__ import annotations

import json

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult
from app.utils.url_helpers import extract_brand_name

SOCIAL_DOMAINS = [
    "linkedin.com", "twitter.com", "x.com", "facebook.com",
    "instagram.com", "youtube.com", "github.com", "tiktok.com",
]


class EntityBrandChecker(BaseChecker):
    check_id = "entity_brand"
    check_number = 16
    name = "Entity & Brand Identity"
    layer = Layer.AUTHORITY_TRUST

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        score = 0.0

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        brand = extract_brand_name(crawl.soup, crawl.url)
        findings.append(f"brand:{brand}")

        # Organization schema + sameAs
        scripts = crawl.soup.find_all("script", type="application/ld+json")
        has_org_schema = False
        same_as_links: list[str] = []

        for script in scripts:
            try:
                data = json.loads(script.string or "")
                objects = []
                if isinstance(data, dict):
                    objects = data.get("@graph", [data])
                elif isinstance(data, list):
                    objects = data

                for obj in objects:
                    obj_type = obj.get("@type", "")
                    if isinstance(obj_type, list):
                        obj_type = " ".join(obj_type)
                    if any(t in obj_type for t in ["Organization", "Corporation", "LocalBusiness"]):
                        has_org_schema = True
                        sa = obj.get("sameAs", [])
                        if isinstance(sa, str):
                            sa = [sa]
                        same_as_links.extend(sa)
            except (json.JSONDecodeError, TypeError):
                pass

        if has_org_schema:
            score += 25
            findings.append("organization_schema_present")
        else:
            findings.append("no_organization_schema")

        if same_as_links:
            score += 10
            findings.append(f"sameAs_links:{len(same_as_links)}")

        # Social links on page
        social_found = []
        for a in crawl.soup.find_all("a", href=True):
            href = a["href"].lower()
            for domain in SOCIAL_DOMAINS:
                if domain in href and domain not in social_found:
                    social_found.append(domain)

        if social_found:
            social_score = min(len(social_found) * 5, 20)
            score += social_score
            findings.append(f"social_links:{','.join(social_found)}")
        else:
            findings.append("no_social_links")

        # Brand in title/H1
        title_tag = crawl.soup.find("title")
        h1_tag = crawl.soup.find("h1")
        brand_lower = brand.lower()

        brand_in_title = title_tag and brand_lower in (title_tag.string or "").lower()
        brand_in_h1 = h1_tag and brand_lower in h1_tag.get_text().lower()

        if brand_in_title or brand_in_h1:
            score += 15
            findings.append("brand_in_title_or_h1")

        # Contact info
        has_contact = bool(
            crawl.soup.find("a", href=lambda h: h and h.startswith("mailto:"))
            or crawl.soup.find("a", href=lambda h: h and h.startswith("tel:"))
        )
        if has_contact:
            score += 10
            findings.append("contact_info_present")

        # Wikipedia link
        for a in crawl.soup.find_all("a", href=True):
            if "wikipedia.org" in a["href"]:
                score += 20
                findings.append("wikipedia_link")
                break

        return self._make_result(score, findings, {"brand": brand, "social": social_found})
