from __future__ import annotations

from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class CrawlData:
    url: str
    html: str = ""
    soup: BeautifulSoup | None = None
    text: str = ""
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    load_time_ms: float = 0.0
    status_code: int = 0
    is_https: bool = False
    headers: dict[str, str] = field(default_factory=dict)
    robots_txt: str | None = None
    sitemap_content: str | None = None
    llm_txt_content: str | None = None
    error: str = ""
