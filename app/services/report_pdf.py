from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from fpdf import FPDF


def render_report_pdf(report: dict) -> bytes:
    """Render a Site Discovery Report as PDF bytes."""
    context = _build_report_context(report)
    pdf = _ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=36)
    pdf.add_page()
    _render_cover(pdf, context)
    pdf.add_page()
    _render_executive_summary(pdf, context)
    _render_methodology(pdf, context)
    _render_sections(pdf, context)
    output = pdf.output(dest="S").encode("latin-1")
    return output


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


class _ReportPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="P", unit="pt", format="A4")
        self.set_margins(left=42, top=36, right=42)

    def footer(self) -> None:
        self.set_y(-28)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 130, 140)
        self.cell(0, 12, f"Page {self.page_no()}", align="R")


def _render_cover(pdf: FPDF, context: dict) -> None:
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(20, 28, 40)
    pdf.cell(0, 28, context["document_type"], ln=1)

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(60, 70, 85)
    pdf.cell(0, 18, f"Prepared for {context['url']}", ln=1)
    pdf.cell(0, 18, f"Generated {context['generated_at_display']}", ln=1)
    pdf.ln(10)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 100, 110)
    pdf.cell(0, 14, "Prepared by Optiminastic Advisory", ln=1)
    pdf.ln(16)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(90, 100, 110)
    pdf.cell(0, 14, "CONFIDENTIAL", ln=1)


def _render_executive_summary(pdf: FPDF, context: dict) -> None:
    _section_title(pdf, "Executive Summary")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 36, 46)
    pdf.multi_cell(0, 16, context.get("executive_summary", "") or "Summary unavailable.")
    pdf.ln(6)

    _section_title(pdf, "Engagement Snapshot")
    stats = context["stats"]
    _table(
        pdf,
        headers=["Sections", "Analyses", "Observations"],
        rows=[[str(stats["section_count"]), str(stats["analysis_count"]), str(stats["observation_count"])]],
        col_widths=[120, 120, 140],
    )

    pdf.ln(6)
    _section_title(pdf, "Section Coverage")
    rows = [
        [s["title"], str(s["analysis_count"]), str(s["observation_count"])]
        for s in context["section_summaries"]
    ]
    _table(pdf, headers=["Section", "Analyses", "Observations"], rows=rows, col_widths=[240, 100, 100])
    pdf.ln(10)


def _render_methodology(pdf: FPDF, context: dict) -> None:
    _section_title(pdf, "Methodology")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 36, 46)
    pdf.multi_cell(0, 16, context.get("methodology", ""))
    pdf.add_page()


def _render_sections(pdf: FPDF, context: dict) -> None:
    for section in context["sections"]:
        _section_title(pdf, section["title"])
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(90, 100, 110)
        if section["description"]:
            pdf.multi_cell(0, 14, section["description"])
            pdf.ln(4)

        for analysis in section["analyses"]:
            _analysis_block(pdf, analysis)

        pdf.add_page()


def _analysis_block(pdf: FPDF, analysis: dict) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(25, 35, 45)
    pdf.multi_cell(0, 16, analysis.get("subject", ""))

    methodology = analysis.get("methodology")
    if methodology:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(90, 100, 110)
        pdf.multi_cell(0, 14, methodology)

    observations = analysis.get("observations") or []
    if observations:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 36, 46)
        for obs in observations:
            pdf.multi_cell(0, 14, f"- {obs}")
    else:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(90, 100, 110)
        pdf.multi_cell(0, 14, "No observations recorded.")

    evidence_items = analysis.get("evidence_items") or []
    if evidence_items:
        pdf.ln(4)
        rows = [[item["key"], item["value"]] for item in evidence_items]
        _table(pdf, headers=["Evidence", "Detail"], rows=rows, col_widths=[160, 260])
        if analysis.get("evidence_truncated"):
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(110, 120, 130)
            pdf.multi_cell(0, 12, "Evidence truncated for brevity.")
    pdf.ln(8)


def _section_title(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(15, 35, 55)
    pdf.cell(0, 18, text, ln=1)


def _table(
    pdf: FPDF,
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[int],
    row_height: int = 16,
) -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(40, 55, 70)
    for header, width in zip(headers, col_widths, strict=False):
        pdf.cell(width, row_height, header, border=1)
    pdf.ln(row_height)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 36, 46)
    for row in rows:
        heights = []
        for value, width in zip(row, col_widths, strict=False):
            heights.append(_calc_cell_height(pdf, value, width, row_height))
        max_height = max(heights) if heights else row_height
        start_x = pdf.get_x()
        start_y = pdf.get_y()

        for value, width in zip(row, col_widths, strict=False):
            x = pdf.get_x()
            y = pdf.get_y()
            pdf.multi_cell(width, row_height, value, border=1)
            pdf.set_xy(x + width, y)
        pdf.set_xy(start_x, start_y + max_height)


def _calc_cell_height(pdf: FPDF, text: str, width: int, row_height: int) -> int:
    if not text:
        return row_height
    words = text.split(" ")
    lines = 1
    line_width = 0
    space_width = pdf.get_string_width(" ")
    for word in words:
        word_width = pdf.get_string_width(word)
        if line_width + word_width <= width:
            line_width += word_width + space_width
        else:
            lines += 1
            line_width = word_width + space_width
    return row_height * lines
