"""Author E-E-A-T checker (#17) — discovers trust & authority signals.

Finds and reports: author attribution, bio/about links, Person schema,
credentials, trust domain links, trust pages, publication dates,
external source diversity, and transparency signals.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult

BYLINE_PATTERNS = re.compile(
    r"(written by|by |author:|posted by|reviewed by|medically reviewed)",
    re.IGNORECASE,
)

TRUST_TLDS = {".gov", ".edu", ".ac.uk", ".gov.uk", ".gov.au", ".edu.au", ".ac.jp"}

TRUST_DOMAINS = {
    "wikipedia.org", "bbc.com", "nytimes.com", "reuters.com",
    "nature.com", "pubmed.ncbi.nlm.nih.gov", "scholar.google.com",
    "forbes.com", "hbr.org", "techcrunch.com", "wsj.com",
    "theguardian.com", "washingtonpost.com", "bloomberg.com",
    "sciencedirect.com", "springer.com", "wiley.com",
    "arxiv.org", "ieee.org", "acm.org",
    "who.int", "cdc.gov", "nih.gov", "fda.gov",
    "harvard.edu", "mit.edu", "stanford.edu", "oxford.ac.uk",
    "cambridge.org", "un.org",
}

CREDENTIAL_PATTERN = re.compile(
    r"(Ph\.?D|M\.?D|MBA|CPA|certified|licensed|professor|expert|specialist)",
    re.IGNORECASE,
)

TRANSPARENCY_KEYWORDS = [
    "disclosure", "editorial policy", "editorial standards",
    "fact-check", "reviewed by", "medically reviewed",
    "affiliate", "sponsored", "advertising policy",
]

ORG_INFO_KEYWORDS = [
    "about us", "our team", "our mission", "founded in",
    "headquarters", "our story",
]


def _is_trust_link(href: str) -> bool:
    try:
        domain = urlparse(href).netloc.lower()
        for trust in TRUST_DOMAINS:
            if domain.endswith(trust):
                return True
        for tld in TRUST_TLDS:
            if domain.endswith(tld):
                return True
    except Exception:
        pass
    return False


class AuthorEeatChecker(BaseChecker):
    check_id = "author_eeat"
    check_number = 17
    name = "Author E-E-A-T"
    layer = Layer.AUTHORITY_TRUST

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        details: dict = {}
        score = 0.0

        if not crawl.soup:
            return self._make_result(0, ["no_html"])

        soup = crawl.soup

        # ── Author byline ─────────────────────────────────────────────
        byline_text = None
        for elem in soup.find_all(["span", "p", "div", "a"], limit=200):
            text = elem.get_text(strip=True)
            if BYLINE_PATTERNS.search(text):
                byline_text = text[:120]
                break

        author_rel_links = soup.find_all("a", rel="author")
        if byline_text or author_rel_links:
            score += 12
            findings.append("author_byline_found")
            if byline_text:
                details["author_byline"] = byline_text
        else:
            findings.append("no_author_byline")

        # ── Author about/bio links ────────────────────────────────────
        about_links = soup.find_all(
            "a", href=re.compile(r"/(about|author|team|bio)", re.I)
        )
        about_hrefs = [a["href"] for a in about_links[:5]]
        if about_hrefs:
            score += 8
            findings.append("author_about_links")
            details["author_about_hrefs"] = about_hrefs
        else:
            findings.append("no_author_about_links")

        # ── Person schema ─────────────────────────────────────────────
        person_data: dict = {}
        scripts = soup.find_all("script", type="application/ld+json")
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
                    if "Person" in str(obj_type):
                        person_data = {
                            "name": obj.get("name"),
                            "jobTitle": obj.get("jobTitle"),
                            "url": obj.get("url"),
                            "sameAs": obj.get("sameAs"),
                            "hasCredential": bool(obj.get("hasCredential")),
                        }
                        break
            except (json.JSONDecodeError, TypeError):
                pass

        if person_data:
            score += 8
            findings.append("person_schema_present")
            details["person_schema"] = {k: v for k, v in person_data.items() if v}
            if person_data.get("jobTitle") or person_data.get("hasCredential"):
                score += 4
                findings.append("author_credentials_in_schema")
        else:
            findings.append("no_person_schema")

        # ── Credentials in text ────────────────────────────────────────
        cred_matches = CREDENTIAL_PATTERN.findall(crawl.text[:3000])
        if cred_matches:
            score += 8
            findings.append("credentials_mentioned")
            details["credentials_found"] = list(set(cred_matches))
        else:
            findings.append("no_credentials_found")

        # ── Trust domain links ─────────────────────────────────────────
        trust_links: list[str] = []
        trust_domains_found: list[str] = []
        for link in crawl.external_links:
            if _is_trust_link(link):
                trust_links.append(link)
                try:
                    trust_domains_found.append(urlparse(link).netloc)
                except Exception:
                    pass

        details["trust_link_count"] = len(trust_links)
        details["trust_domains"] = sorted(set(trust_domains_found))
        if trust_links:
            findings.append(f"trust_links_found:{len(trust_links)}")
            score += min(12, len(trust_links) * 4)
        else:
            findings.append("no_trust_links")

        # ── Trust pages ────────────────────────────────────────────────
        nav_links = set()
        for a in soup.find_all("a", href=True):
            nav_links.add(a["href"].lower())
            nav_links.add(a.get_text(strip=True).lower())

        nav_list = list(nav_links)
        trust_pages_found: list[str] = []
        for page, keywords in [
            ("about", ["about"]),
            ("contact", ["contact"]),
            ("privacy", ["privacy"]),
            ("terms", ["terms", "tos"]),
        ]:
            if any(kw in x for x in nav_list for kw in keywords):
                trust_pages_found.append(page)

        details["trust_pages"] = trust_pages_found
        if trust_pages_found:
            findings.append(f"trust_pages_found:{','.join(trust_pages_found)}")
            score += min(10, len(trust_pages_found) * 3)
        else:
            findings.append("no_trust_pages")

        # ── Publication date ───────────────────────────────────────────
        pub_date = None
        time_tag = soup.find("time", attrs={"datetime": True})
        if time_tag:
            pub_date = time_tag["datetime"]
        if not pub_date:
            meta = soup.find("meta", property="article:published_time")
            if meta and meta.get("content"):
                pub_date = meta["content"]
        if not pub_date:
            for script in scripts:
                try:
                    data = json.loads(script.string or "")
                    objs = data.get("@graph", [data]) if isinstance(data, dict) else data
                    for obj in objs:
                        if isinstance(obj, dict) and obj.get("datePublished"):
                            pub_date = obj["datePublished"]
                            break
                except (json.JSONDecodeError, TypeError):
                    pass
                if pub_date:
                    break

        if pub_date:
            details["publication_date"] = str(pub_date)[:20]
            findings.append("publication_date_found")
            score += 10
        else:
            findings.append("no_publication_date")

        # Check for modified date too
        mod_date = None
        meta_mod = soup.find("meta", property="article:modified_time")
        if meta_mod and meta_mod.get("content"):
            mod_date = meta_mod["content"]
        if mod_date:
            details["modified_date"] = str(mod_date)[:20]
            findings.append("modified_date_found")

        # ── Source diversity ───────────────────────────────────────────
        ext_domains = set()
        for link in crawl.external_links:
            try:
                ext_domains.add(urlparse(link).netloc)
            except Exception:
                pass
        details["external_domains"] = sorted(ext_domains)
        details["source_diversity"] = len(ext_domains)
        if ext_domains:
            findings.append(f"external_domains_found:{len(ext_domains)}")
            score += min(10, len(ext_domains) * 2)
        else:
            findings.append("no_external_links")

        # ── Transparency signals ───────────────────────────────────────
        html_lower = crawl.html.lower()
        transparency_found: list[str] = []
        for kw in TRANSPARENCY_KEYWORDS:
            if kw in html_lower:
                transparency_found.append(kw)
        org_info_found: list[str] = []
        for kw in ORG_INFO_KEYWORDS:
            if kw in html_lower:
                org_info_found.append(kw)

        details["transparency_signals"] = transparency_found
        details["org_info_signals"] = org_info_found
        if transparency_found:
            findings.append(f"transparency_signals:{','.join(transparency_found)}")
            score += 4
        if org_info_found:
            findings.append(f"org_info_signals:{','.join(org_info_found)}")
            score += 4
        if not transparency_found and not org_info_found:
            findings.append("no_transparency_signals")

        return self._make_result(score, findings, details)
