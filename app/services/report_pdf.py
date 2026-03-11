from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa


def render_report_pdf(report: dict) -> bytes:
    """Render a Site Discovery Report as PDF bytes."""
    context = _build_report_context(report)
    html = _render_template("report.html", context)
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_buffer, encoding="utf-8")
    if pisa_status.err:
        raise RuntimeError("PDF generation failed")
    pdf_buffer.seek(0)
    return pdf_buffer.read()


def _render_template(template_name: str, context: dict) -> str:
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template(template_name)
    return template.render(**context)


def _build_report_context(report: dict) -> dict:
    generated_at = _parse_timestamp(report.get("generated_at"))
    generated_at_display = (
        generated_at.astimezone(timezone.utc).strftime("%B %d, %Y %H:%M UTC")
        if generated_at
        else "Unknown"
    )

    sections = []
    total_analyses = 0
    total_observations = 0

    for section in report.get("sections", []):
        analyses = []
        for analysis in section.get("analyses", []):
            observations = analysis.get("observations") or []
            evidence_items, evidence_truncated = _flatten_evidence(analysis.get("evidence", {}))
            analyses.append(
                {
                    "subject": analysis.get("subject", ""),
                    "methodology": analysis.get("methodology", ""),
                    "observations": observations,
                    "evidence_items": evidence_items,
                    "evidence_truncated": evidence_truncated,
                }
            )
            total_observations += len(observations)
        total_analyses += len(analyses)
        sections.append(
            {
                "title": section.get("title", ""),
                "description": section.get("description", ""),
                "analyses": analyses,
            }
        )

    section_summaries = []
    for section in sections:
        observation_count = sum(len(a["observations"]) for a in section["analyses"])
        section_summaries.append(
            {
                "title": section["title"],
                "analysis_count": len(section["analyses"]),
                "observation_count": observation_count,
            }
        )

    return {
        "document_type": report.get("document_type", "Site Discovery Report"),
        "generated_at_display": generated_at_display,
        "url": report.get("url", ""),
        "executive_summary": report.get("executive_summary", ""),
        "methodology": report.get("methodology", ""),
        "sections": sections,
        "section_summaries": section_summaries,
        "stats": {
            "section_count": len(sections),
            "analysis_count": total_analyses,
            "observation_count": total_observations,
        },
    }


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _flatten_evidence(evidence: Any) -> tuple[list[dict], bool]:
    if not isinstance(evidence, dict):
        return ([], False)

    items: list[dict] = []
    for key, value in evidence.items():
        items.append({"key": _safe_text(key), "value": _format_value(value)})

    max_items = 12
    truncated = len(items) > max_items
    return (items[:max_items], truncated)


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"{value}"
    if isinstance(value, str):
        return _safe_text(value)
    if isinstance(value, list):
        sample = [_safe_text(str(v)) for v in value[:6]]
        suffix = "..." if len(value) > 6 else ""
        return ", ".join(sample) + suffix
    if isinstance(value, dict):
        parts = []
        for k, v in list(value.items())[:6]:
            parts.append(f"{_safe_text(str(k))}: {_safe_text(str(v))}")
        suffix = "..." if len(value) > 6 else ""
        return "; ".join(parts) + suffix
    return _safe_text(str(value))


def _safe_text(text: str) -> str:
    clean = text.replace("\n", " ").replace("\r", " ").strip()
    return _soft_wrap_tokens(clean, 28)


def _soft_wrap_tokens(text: str, max_len: int) -> str:
    parts = []
    for token in text.split(" "):
        if len(token) <= max_len:
            parts.append(token)
            continue
        chunks = [token[i : i + max_len] for i in range(0, len(token), max_len)]
        parts.append(" ".join(chunks))
    return " ".join(parts)
