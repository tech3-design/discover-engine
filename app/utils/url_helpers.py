from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

_GENERIC_PARTS = {
    "www", "com", "net", "org", "io", "co", "uk", "de", "fr",
    "app", "ai", "dev", "ui", "api", "get", "try",
}


def extract_domain(url: str) -> str:
    netloc = urlparse(url).netloc
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def extract_internal_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    base_netloc = urlparse(base_url).netloc
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.scheme in ("http", "https") and parsed.netloc == base_netloc:
            links.append(full)
    return links


def extract_external_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract all external links (different domain from page)."""
    base_netloc = urlparse(base_url).netloc
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if (
            parsed.scheme in ("http", "https")
            and parsed.netloc
            and parsed.netloc != base_netloc
        ):
            links.append(full)
    return links


def extract_brand_name(soup: BeautifulSoup, url: str) -> str:
    # 1. og:site_name
    og = soup.find("meta", property="og:site_name")
    if og and og.get("content", "").strip():
        return og["content"].strip()

    # 2. <title> — first segment before separator
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        import re
        parts = re.split(r"[|\-–—:]", title_tag.string)
        brand = parts[0].strip()
        if brand and brand.lower() not in _GENERIC_PARTS:
            return brand

    # 3. Domain fallback
    domain = extract_domain(url)
    name = domain.split(".")[0]
    if name.lower() not in _GENERIC_PARTS:
        return name.capitalize()
    return domain
