from __future__ import annotations

from app.checkers.base import BaseChecker
from app.models.enums import Layer
from app.models.crawl_data import CrawlData
from app.models.responses import CheckResult

AI_BOTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "GoogleOther", "CCBot", "ChatGPT-User"]


class RobotsTxtChecker(BaseChecker):
    check_id = "robots_txt"
    check_number = 1
    name = "Robots.txt Correctness"
    layer = Layer.SITE_FOUNDATION

    async def run(self, crawl: CrawlData) -> CheckResult:
        findings: list[str] = []
        score = 0.0

        if crawl.robots_txt is None:
            findings.append("robots_txt_missing")
            return self._make_result(0, findings)

        content = crawl.robots_txt
        score += 30  # exists
        findings.append("robots_txt_exists")

        # Check for blanket Disallow: /
        lines = content.lower().splitlines()
        has_blanket_block = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("disallow") and stripped.replace(" ", "").endswith(":/"):
                has_blanket_block = True
                break

        if not has_blanket_block:
            score += 20
            findings.append("no_blanket_disallow")
        else:
            findings.append("blanket_disallow_found")

        # Check sitemap directive
        if "sitemap:" in content.lower():
            score += 10
            findings.append("sitemap_directive_present")

        # Check AI bot access
        blocked_bots = []
        for bot in AI_BOTS:
            bot_lower = bot.lower()
            for i, line in enumerate(lines):
                if f"user-agent: {bot_lower}" in line.replace(" ", "").lower().replace("user-agent:", "user-agent: "):
                    # Check next disallow lines
                    for next_line in lines[i + 1:]:
                        next_stripped = next_line.strip()
                        if next_stripped.startswith("user-agent"):
                            break
                        if "disallow: /" in next_stripped.replace(" ", "").lower().replace("disallow:", "disallow: "):
                            blocked_bots.append(bot)
                            break

        if not blocked_bots:
            score += 40
            findings.append("ai_bots_allowed")
        else:
            # Partial score — some bots blocked
            allowed_ratio = (len(AI_BOTS) - len(blocked_bots)) / len(AI_BOTS)
            score += 40 * allowed_ratio
            findings.append(f"ai_bots_blocked: {', '.join(blocked_bots)}")

        return self._make_result(score, findings, {"blocked_bots": blocked_bots})
