from __future__ import annotations

from bs4 import BeautifulSoup, Tag


def extract_text(soup: BeautifulSoup) -> str:
    """Extract visible text from HTML, stripping boilerplate elements."""
    clone = BeautifulSoup(str(soup), "lxml")
    for tag in clone.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return " ".join(clone.get_text(separator=" ").split())


def count_words(text: str) -> int:
    return len(text.split())


def safe_score(value: float, max_val: float = 100.0) -> float:
    """Clamp score between 0 and max_val."""
    return max(0.0, min(float(value), max_val))
