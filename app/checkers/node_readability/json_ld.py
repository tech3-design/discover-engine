"""JSON-LD Structured Data checker (#14) — v2 upgrade with full property maps.

Ported from Django analyzer pipeline/schema.py with 19-type required/recommended maps.

Scoring (100 pts):
  20 — JSON-LD presence
  10 — Valid schema.org context
  40 — Schema completeness (70% required + 30% recommended)
  15 — Schema type variety
  15 — Date metadata freshness
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult

# Full 19-type required property maps (ported from Django schema.py)
REQUIRED_PROPS: dict[str, set[str]] = {
    "FAQPage": {"mainEntity"},
    "Article": {"headline", "author", "datePublished"},
    "NewsArticle": {"headline", "author", "datePublished"},
    "BlogPosting": {"headline", "author", "datePublished"},
    "Organization": {"name", "url"},
    "LocalBusiness": {"name", "address"},
    "Product": {"name"},
    "HowTo": {"name", "step"},
    "BreadcrumbList": {"itemListElement"},
    "WebSite": {"name", "url"},
    "WebPage": {"name"},
    "VideoObject": {"name", "uploadDate"},
    "Event": {"name", "startDate"},
    "Review": {"itemReviewed", "reviewRating"},
    "AggregateRating": {"ratingValue", "reviewCount"},
    "SoftwareApplication": {"name"},
    "Service": {"name"},
    "SpeakableSpecification": {"cssSelector"},
    "Person": {"name"},
    "ItemList": {"itemListElement"},
}

RECOMMENDED_PROPS: dict[str, set[str]] = {
    "FAQPage": set(),
    "Article": {"image", "publisher", "dateModified", "description"},
    "NewsArticle": {"image", "publisher", "dateModified", "description"},
    "BlogPosting": {"image", "publisher", "dateModified", "description"},
    "Organization": {"logo", "sameAs", "description", "contactPoint", "address"},
    "LocalBusiness": {"telephone", "openingHours", "geo"},
    "Product": {"description", "image", "offers", "brand", "review", "aggregateRating"},
    "HowTo": {"description", "image", "totalTime"},
    "BreadcrumbList": set(),
    "WebSite": {"potentialAction", "description"},
    "WebPage": {"description", "datePublished"},
    "VideoObject": {"description", "thumbnailUrl", "duration"},
    "Event": {"location", "description", "endDate"},
    "Review": {"author", "datePublished"},
    "AggregateRating": {"bestRating"},
    "SoftwareApplication": {"applicationCategory", "offers", "operatingSystem"},
    "Service": {"description", "provider", "areaServed"},
    "SpeakableSpecification": {"xpath"},
    "Person": {"jobTitle", "url", "sameAs", "affiliation"},
    "ItemList": set(),
}


def _compute_completeness(obj: dict, schema_type: str) -> tuple[float, dict]:
    """Score a single schema object on property completeness. Returns (0.0-1.0, report)."""
    required = REQUIRED_PROPS.get(schema_type, set())
    recommended = RECOMMENDED_PROPS.get(schema_type, set())
    report: dict = {
        "required_present": [], "required_missing": [],
        "recommended_present": [], "recommended_missing": [],
    }

    for prop in required:
        val = obj.get(prop)
        if val is not None and val != "" and val != [] and val != {}:
            report["required_present"].append(prop)
        else:
            report["required_missing"].append(prop)

    for prop in recommended:
        val = obj.get(prop)
        if val is not None and val != "" and val != [] and val != {}:
            report["recommended_present"].append(prop)
        else:
            report["recommended_missing"].append(prop)

    req_total = len(required)
    rec_total = len(recommended)
    req_score = len(report["required_present"]) / req_total if req_total else 1.0
    rec_score = len(report["recommended_present"]) / rec_total if rec_total else 1.0

    completeness = req_score * 0.7 + rec_score * 0.3
    return completeness, report


def _get_all_objects(schema: dict) -> list[dict]:
    """Flatten schema into individual typed objects (handles @graph)."""
    objects = []
    if "@type" in schema:
        objects.append(schema)
    for item in schema.get("@graph", []):
        if isinstance(item, dict):
            objects.extend(_get_all_objects(item))
    return objects


class JsonLdChecker(BaseChecker):
    check_id = "json_ld"
    check_number = 14
    name = "JSON-LD Structured Data"
    layer = Layer.NODE_READABILITY

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        score = 0.0
        details: dict = {"completeness": {}}

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        scripts = crawl.soup.find_all("script", type="application/ld+json")
        if not scripts:
            findings.append("no_json_ld")
            return self._make_result(0, findings)

        # ── JSON-LD presence (20 pts) ──────────────────────────────────
        score += 20
        findings.append("json_ld_present")

        # Parse all JSON-LD blocks
        schemas: list[dict] = []
        for script in scripts:
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    schemas.append(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            schemas.append(item)
            except (json.JSONDecodeError, TypeError):
                findings.append("json_ld_parse_error")

        if not schemas:
            return self._make_result(score, findings)

        # Flatten all objects
        all_objects: list[dict] = []
        for s in schemas:
            all_objects.extend(_get_all_objects(s))

        # Collect all types
        all_types: set[str] = set()
        for s in schemas:
            t = s.get("@type", "")
            if isinstance(t, list):
                all_types.update(t)
            elif isinstance(t, str) and t:
                all_types.add(t)
            for item in s.get("@graph", []):
                if isinstance(item, dict):
                    it = item.get("@type", "")
                    if isinstance(it, list):
                        all_types.update(it)
                    elif isinstance(it, str) and it:
                        all_types.add(it)

        # ── Valid @context (10 pts) ────────────────────────────────────
        has_valid_context = any(
            "schema.org" in str(obj.get("@context", "")) for obj in schemas
        )
        if has_valid_context:
            score += 10
            findings.append("valid_schema_context")

        # ── Completeness (40 pts) — 70/30 weighted formula ────────────
        scored_types: set[str] = set()
        completeness_scores: list[float] = []

        for obj in all_objects:
            obj_type = obj.get("@type", "")
            obj_types = obj_type if isinstance(obj_type, list) else [obj_type]

            for schema_type in obj_types:
                if schema_type in scored_types:
                    continue
                if schema_type not in REQUIRED_PROPS:
                    continue

                scored_types.add(schema_type)
                completeness, report = _compute_completeness(obj, schema_type)
                completeness_scores.append(completeness)

                details["completeness"][schema_type] = {
                    "score": round(completeness * 100),
                    "required_present": report["required_present"],
                    "required_missing": report["required_missing"],
                    "recommended_present": report["recommended_present"],
                    "recommended_missing": report["recommended_missing"],
                }

                if report["required_missing"]:
                    findings.append(f"schema_incomplete:{schema_type}")

        if completeness_scores:
            avg_completeness = sum(completeness_scores) / len(completeness_scores)
            score += avg_completeness * 40
            findings.append(f"schema_completeness:{avg_completeness:.0%}")

        # ── Variety bonus (15 pts) ─────────────────────────────────────
        unique_types = all_types
        if len(unique_types) >= 5:
            score += 15
        elif len(unique_types) >= 3:
            score += 10
        elif len(unique_types) >= 2:
            score += 6
        elif len(unique_types) >= 1:
            score += 3
        findings.append(f"schema_types:{','.join(sorted(unique_types))}")

        # ── Date metadata freshness (15 pts) ───────────────────────────
        current_year = datetime.now(timezone.utc).year
        date_found = False
        for obj in all_objects:
            date_val = obj.get("dateModified", "") or obj.get("datePublished", "")
            if date_val:
                try:
                    year_match = re.search(r"(\d{4})", str(date_val))
                    if year_match:
                        content_year = int(year_match.group(1))
                        if content_year >= current_year - 1:
                            score += 15
                            date_found = True
                            break
                        else:
                            score += 8
                            date_found = True
                            break
                except Exception:
                    pass
        if date_found:
            findings.append("date_metadata_present")

        return self._make_result(score, findings, {"types": sorted(unique_types), **details})
