#!/usr/bin/env python3
"""
Generate Lifeway_EMR_User_Manual.pdf from the Markdown manual.
Requires: pip install markdown weasyprint
Alternative (no weasyprint): pip install markdown pdfkit  (and wkhtmltopdf on system)
Or use: pip install reportlab
This script uses reportlab for minimal dependencies (no weasyprint/wkhtmltopdf).
"""
import os
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

def escape_html(s):
    """Escape < and > so they don't break Paragraph."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def md_line_to_flow(line, styles):
    """Convert a markdown line to ReportLab flowable. Simple handling."""
    line = line.rstrip()
    if not line:
        return Spacer(1, 6)
    if re.match(r"^---+$", line):
        return Spacer(1, 12)
    # Headers
    if line.startswith("# "):
        return Paragraph(escape_html(line[2:].strip()), styles["Heading1"])
    if line.startswith("## "):
        return Paragraph(escape_html(line[3:].strip()), styles["Heading2"])
    if line.startswith("### "):
        return Paragraph(escape_html(line[4:].strip()), styles["Heading3"])
    # Numbered list or bullet
    if re.match(r"^\d+\.\s", line) or line.strip().startswith("- "):
        text = escape_html(line.strip())
        text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
        return Paragraph("&#8226; " + text, styles["Normal"])
    # Bold: **text** -> <b>text</b> (after escape so we only bold safe content)
    text = escape_html(line)
    text = re.sub(r"&lt;\s*b\s*&gt;\s*([^&]+)\s*&lt;\s*/\s*b\s*&gt;", r"<b>\1</b>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    return Paragraph(text, styles["Normal"])

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_path = os.path.join(script_dir, "Lifeway_EMR_User_Manual.md")
    pdf_path = os.path.join(script_dir, "Lifeway_EMR_User_Manual.pdf")

    if not os.path.exists(md_path):
        print(f"Error: {md_path} not found")
        return 1

    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    styles["Heading1"].fontSize = 16
    styles["Heading1"].spaceAfter = 12
    styles["Heading1"].textColor = "darkblue"
    styles["Heading2"].fontSize = 14
    styles["Heading2"].spaceAfter = 8
    styles["Heading2"].textColor = "navy"
    styles["Heading3"].fontSize = 12
    styles["Heading3"].spaceAfter = 6
    styles["Normal"].spaceAfter = 4

    story = []
    for line in lines:
        flow = md_line_to_flow(line, styles)
        story.append(flow)

    doc.build(story)
    print(f"PDF saved to: {pdf_path}")
    return 0

if __name__ == "__main__":
    exit(main())
