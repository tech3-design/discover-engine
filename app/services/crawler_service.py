from __future__ import annotations

import asyncio
import time
from urllib.parse import urljoin

import httpx
import structlog
from bs4 import BeautifulSoup

from app.config import settings
from app.models.crawl_data import CrawlData
from app.utils.html_helpers import extract_text
from app.utils.url_helpers import extract_external_links, extract_internal_links

logger = structlog.get_logger()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

_ua_index = 0


def _next_ua() -> str:
    global _ua_index
    ua = USER_AGENTS[_ua_index % len(USER_AGENTS)]
    _ua_index += 1
    return ua


async def _fetch_optional(client: httpx.AsyncClient, url: str) -> str | None:
    """Fetch a URL, returning content or None on failure."""
    try:
        resp = await client.get(url, follow_redirects=True, timeout=10)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


async def crawl_url(url: str) -> CrawlData:
    """Crawl a URL and pre-fetch robots.txt, sitemap.xml, llm.txt."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    timeout = httpx.Timeout(settings.crawler_timeout)
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": _next_ua()},
        follow_redirects=True,
    ) as client:
        # Fetch page + auxiliary files in parallel
        start = time.monotonic()

        page_task = _fetch_page(client, url)
        robots_task = _fetch_optional(client, f"{base}/robots.txt")
        sitemap_task = _fetch_optional(client, f"{base}/sitemap.xml")
        llm_task = _fetch_optional(client, f"{base}/.well-known/llms.txt")

        page_result, robots_txt, sitemap_content, llm_txt = await asyncio.gather(
            page_task, robots_task, sitemap_task, llm_task
        )

        load_time_ms = (time.monotonic() - start) * 1000

    status_code, html, headers, error = page_result

    if error:
        return CrawlData(url=url, error=error, status_code=status_code)

    soup = BeautifulSoup(html, "lxml")
    text = extract_text(soup)
    internal_links = extract_internal_links(soup, url)
    external_links = extract_external_links(soup, url)

    return CrawlData(
        url=url,
        html=html,
        soup=soup,
        text=text,
        internal_links=internal_links,
        external_links=external_links,
        load_time_ms=load_time_ms,
        status_code=status_code,
        is_https=parsed.scheme == "https",
        headers=dict(headers),
        robots_txt=robots_txt,
        sitemap_content=sitemap_content,
        llm_txt_content=llm_txt,
    )


async def _fetch_page(
    client: httpx.AsyncClient, url: str
) -> tuple[int, str, dict, str]:
    """Fetch page with retry. Returns (status, html, headers, error)."""
    max_retries = settings.crawler_max_retries
    for attempt in range(max_retries + 1):
        try:
            resp = await client.get(url)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                await asyncio.sleep(2 ** (attempt + 1))
                continue
            return resp.status_code, resp.text, resp.headers, ""
        except httpx.TimeoutException:
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            return 0, "", {}, "Timeout"
        except httpx.ConnectError:
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            return 0, "", {}, "Connection error"
        except Exception as exc:
            return 0, "", {}, str(exc)
    return 0, "", {}, "Max retries exceeded"
