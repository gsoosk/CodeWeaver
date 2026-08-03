"""Tests for experiments/recodeagent/render.py: Markdown table/report
rendering (deterministic, byte-for-byte) and PDF rendering via reportlab with
graceful degradation when it is unavailable. No network, LLM, or toolchain
access -- pure text/PDF generation from in-memory data.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from experiments.recodeagent import common as C
from experiments.recodeagent import render as RD


# --------------------------------------------------------------------------- #
# markdown_table
# --------------------------------------------------------------------------- #
def test_markdown_table_basic_shape():
    text = RD.markdown_table(["a", "b"], [[1, 2], [3, 4]])
    lines = text.splitlines()
    assert lines[0] == "| a | b |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| 1 | 2 |"
    assert lines[3] == "| 3 | 4 |"


def test_markdown_table_none_cells_render_empty_not_literal_none():
    text = RD.markdown_table(["a"], [[None]])
    assert "| None |" not in text
    assert "|  |" in text or text.splitlines()[-1] == "|  |"


def test_markdown_table_float_formatting():
    text = RD.markdown_table(["frac"], [[0.5]])
    assert "0.5000" in text


def test_markdown_table_empty_rows():
    text = RD.markdown_table(["a", "b"], [])
    lines = text.splitlines()
    assert len(lines) == 2   # header + separator only


# --------------------------------------------------------------------------- #
# ReportSection / render_markdown_report
# --------------------------------------------------------------------------- #
def test_render_markdown_report_includes_title_and_headings():
    sections = [RD.ReportSection("Section One", "body one", level=2), RD.ReportSection("Section Two", "body two", level=3)]
    text = RD.render_markdown_report("My Title", sections)
    assert text.startswith("# My Title")
    assert "## Section One" in text
    assert "### Section Two" in text
    assert "body one" in text
    assert "body two" in text


def test_render_markdown_report_is_deterministic():
    sections = [RD.ReportSection("A", "x", level=2)]
    t1 = RD.render_markdown_report("T", sections)
    t2 = RD.render_markdown_report("T", sections)
    assert t1 == t2


def test_render_markdown_report_empty_sections():
    text = RD.render_markdown_report("Only Title", [])
    assert text.strip() == "# Only Title"


def test_write_markdown_report_creates_file(tmp_path: Path):
    sections = [RD.ReportSection("A", "body", level=2)]
    path = RD.write_markdown_report("Title", sections, tmp_path / "report.md")
    assert path.exists()
    assert "# Title" in path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# render_pdf_report
# --------------------------------------------------------------------------- #
def test_render_pdf_report_writes_real_pdf_when_reportlab_available(tmp_path: Path):
    if C.optional_import("reportlab") is None:
        pytest.skip("reportlab not installed in this environment")
    sections = [RD.ReportSection("Heading", "Some body text.\nSecond line.", level=2)]
    path = tmp_path / "report.pdf"
    ok = RD.render_pdf_report("Title", sections, path)
    assert ok is True
    assert path.exists()
    assert path.stat().st_size > 0


def test_render_pdf_report_handles_markdown_table_body(tmp_path: Path):
    if C.optional_import("reportlab") is None:
        pytest.skip("reportlab not installed in this environment")
    body = RD.markdown_table(["a", "b"], [[1, 2]])
    sections = [RD.ReportSection("Table Section", body, level=2)]
    path = tmp_path / "report.pdf"
    ok = RD.render_pdf_report("Title", sections, path)
    assert ok is True
    assert path.exists()


def test_render_pdf_report_placeholder_when_reportlab_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(RD.C, "optional_import", lambda name: None)
    sections = [RD.ReportSection("Heading", "body", level=2)]
    path = tmp_path / "report.pdf"
    ok = RD.render_pdf_report("Title", sections, path)
    assert ok is False
    assert not path.exists()
    notice = Path(str(path) + ".unavailable.txt")
    assert notice.exists()
    assert "reportlab" in notice.read_text(encoding="utf-8")


def test_render_pdf_report_empty_sections_still_writes(tmp_path: Path):
    if C.optional_import("reportlab") is None:
        pytest.skip("reportlab not installed in this environment")
    path = tmp_path / "report.pdf"
    ok = RD.render_pdf_report("Only Title", [], path)
    assert ok is True
    assert path.exists()
