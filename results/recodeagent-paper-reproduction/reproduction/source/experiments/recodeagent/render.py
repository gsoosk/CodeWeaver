"""render.py -- generic Markdown + PDF rendering primitives for narrative
(section-based) documents, used by report.py to produce the final
``reproducibility_report.md``/``.pdf``.

This is deliberately separate from analyze.py's table/figure renderers:
analyze.py renders DATA (rows/columns, bar charts); this module renders
PROSE (headings + body text, optionally containing a Markdown table) for a
human to read top-to-bottom. Both independently degrade gracefully when
reportlab is not installed (writing a plain-text ``*.pdf.unavailable.txt``
sibling instead of failing outright).

Deterministic: given the same title/sections, ``render_markdown_report``
produces byte-identical output every time, and ``render_pdf_report`` produces
structurally identical content (the PDF body is the literal section text,
via reportlab's ``Preformatted`` flowable -- no Markdown-to-HTML parsing, no
hidden non-deterministic layout state). Any inherently-varying content (e.g.
a "generated_at" timestamp) must be passed by the caller as ordinary section
text, never smuggled in as hidden metadata that could make the Markdown and
PDF drift apart.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from experiments.recodeagent import common as C
from experiments.recodeagent.common import atomic_write_text


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    """Renders a GitHub-flavored Markdown table. ``None`` cells render as an
    empty string (never the literal text "None"), consistent with the rest
    of the harness's CSV writers."""
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_cell_text(v) for v in row) + " |")
    return "\n".join(lines)


class ReportSection:
    """One heading + Markdown-formatted body block. ``level`` is a Markdown
    heading level (2 = ``##``) and also selects the reportlab heading style
    (H1/H2/H3; anything deeper falls back to H3) in the PDF rendering."""

    __slots__ = ("heading", "body", "level")

    def __init__(self, heading: str, body: str, *, level: int = 2):
        self.heading = heading
        self.body = body
        self.level = level

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"ReportSection(heading={self.heading!r}, level={self.level})"


def render_markdown_report(title: str, sections: list[ReportSection]) -> str:
    lines = [f"# {title}", ""]
    for s in sections:
        lines.append(f"{'#' * max(1, s.level)} {s.heading}")
        lines.append("")
        lines.append(s.body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_markdown_report(title: str, sections: list[ReportSection], path: Path) -> Path:
    atomic_write_text(path, render_markdown_report(title, sections))
    return Path(path)


def render_pdf_report(title: str, sections: list[ReportSection], path: Path) -> bool:
    """Returns True if a real PDF was written; False (with a
    ``*.pdf.unavailable.txt`` sibling explaining why) if reportlab is not
    installed. Never raises for a missing optional dependency."""
    reportlab = C.optional_import("reportlab")
    if reportlab is None:
        atomic_write_text(Path(str(path) + ".unavailable.txt"),
                          f"{title}\n\nPDF not rendered: reportlab is not installed in this environment. "
                          f"See the sibling .md for the same content.\n")
        return False
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    heading_style_by_level = {1: styles["Heading1"], 2: styles["Heading2"], 3: styles["Heading3"]}
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    elements: list[Any] = [Paragraph(title, styles["Title"]), Spacer(1, 16)]
    for s in sections:
        elements.append(Paragraph(s.heading, heading_style_by_level.get(s.level, styles["Heading3"])))
        elements.append(Spacer(1, 6))
        # Preformatted (not Paragraph) so the body renders as literal text --
        # no HTML-like markup interpretation/escaping needed, and the PDF is
        # provably the same content as the Markdown sibling.
        elements.append(Preformatted(s.body, styles["Code"]))
        elements.append(Spacer(1, 14))
    doc.build(elements)
    return True
