"""
Converts every .md in output/md/ to a styled .pdf in output/pdf/.

Usage:
    python convert_to_pdf.py                 # converts all files in output/md/
    python convert_to_pdf.py react-js.md      # converts just one file
"""

import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, HRFlowable
from xml.sax.saxutils import escape

from config import DEFAULT_THEME, OUTPUT_MD_DIR, OUTPUT_PDF_DIR, get_theme_for_topic


def _build_styles(theme: dict):
    styles = getSampleStyleSheet()
    accent = colors.HexColor(theme.get("accent", DEFAULT_THEME["accent"]))
    text_on_accent = colors.HexColor(theme.get("text_on_accent", DEFAULT_THEME["text_on_accent"]))
    styles.add(ParagraphStyle(name="NotesTitle", parent=styles["Heading1"], fontSize=20, leading=24, textColor=text_on_accent, spaceAfter=10))
    styles.add(ParagraphStyle(name="NotesH1", parent=styles["Heading1"], fontSize=16, leading=20, textColor=accent, spaceBefore=8, spaceAfter=8))
    styles.add(ParagraphStyle(name="NotesH2", parent=styles["Heading2"], fontSize=13, leading=16, textColor=accent, spaceBefore=6, spaceAfter=6))
    styles.add(ParagraphStyle(name="NotesH3", parent=styles["Heading3"], fontSize=11.5, leading=14, textColor=accent, spaceBefore=4, spaceAfter=4))
    styles.add(ParagraphStyle(name="NotesBody", parent=styles["BodyText"], leading=14.5, spaceAfter=5, fontSize=10.5, textColor=colors.HexColor("#1a1a1a")))
    styles.add(ParagraphStyle(name="NotesBullet", parent=styles["BodyText"], leftIndent=14, leading=14.5, spaceAfter=3, fontSize=10.2))
    styles.add(
        ParagraphStyle(
            name="NotesCode",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=8.7,
            leading=10.2,
            textColor=colors.HexColor("#102a43"),
            backColor=colors.HexColor("#f8fafc"),
            borderColor=accent,
            borderWidth=0.9,
            borderPadding=(8, 8, 8),
        )
    )
    return styles


def _code_font_size_for(lines: list[str]) -> float:
    longest = max((len(line) for line in lines), default=0)
    if longest <= 72:
        return 9.0
    if longest <= 96:
        return 8.2
    if longest <= 120:
        return 7.6
    return 7.0


def _story_from_markdown(md_text: str, theme: dict):
    styles = _build_styles(theme)
    story = []
    in_code = False
    code_lines = []
    seen_title = False

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                code_style = ParagraphStyle(
                    name="AdaptiveCode",
                    parent=styles["NotesCode"],
                    fontSize=_code_font_size_for(code_lines),
                    leading=max(8.5, _code_font_size_for(code_lines) + 1.3),
                )
                story.append(
                    Preformatted(
                        "\n".join(code_lines),
                        code_style,
                    )
                )
                story.append(Spacer(1, 0.12 * inch))
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            story.append(Spacer(1, 0.12 * inch))
            continue

        if stripped.startswith("# "):
            if not seen_title:
                seen_title = True
                continue
            else:
                story.append(Paragraph(escape(stripped[2:]), styles["NotesH1"]))
        elif stripped.startswith("## "):
            story.append(Paragraph(escape(stripped[3:]), styles["NotesH2"]))
        elif stripped.startswith("### "):
            story.append(Paragraph(escape(stripped[4:]), styles["NotesH3"]))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            story.append(Paragraph(f"• {escape(stripped[2:])}", styles["NotesBullet"]))
        else:
            story.append(Paragraph(escape(stripped), styles["NotesBody"]))

        if stripped.startswith("## "):
            story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#d8dee9"), spaceBefore=4, spaceAfter=8))

    return story


def _cover_page(canvas, document, theme: dict, title: str):
    accent = colors.HexColor(theme.get("accent", DEFAULT_THEME["accent"]))
    text_on_accent = colors.HexColor(theme.get("text_on_accent", DEFAULT_THEME["text_on_accent"]))
    label = theme.get("label")
    width, height = document.pagesize
    band_height = 1.35 * inch

    canvas.saveState()
    canvas.setFillColor(accent)
    canvas.rect(0, height - band_height, width, band_height, fill=1, stroke=0)

    canvas.setFillColor(text_on_accent)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(0.75 * inch, height - 0.85 * inch, title)

    if label:
        canvas.setFont("Helvetica-Bold", 8.5)
        badge_width = max(1.0 * inch, canvas.stringWidth(label, "Helvetica-Bold", 8.5) + 16)
        badge_x = 0.75 * inch
        badge_y = height - 1.15 * inch
        canvas.setFillColor(colors.white)
        canvas.roundRect(badge_x, badge_y, badge_width, 0.24 * inch, 0.08 * inch, fill=1, stroke=0)
        canvas.setFillColor(accent)
        canvas.drawString(badge_x + 8, badge_y + 0.075 * inch, label)

    canvas.restoreState()


def convert_file(md_filename: str):
    md_path = os.path.join(OUTPUT_MD_DIR, md_filename)
    if not os.path.exists(md_path):
        print(f"  Skipping — not found: {md_path}")
        return False

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    topic = os.path.splitext(md_filename)[0]
    theme = get_theme_for_topic(topic)

    os.makedirs(OUTPUT_PDF_DIR, exist_ok=True)
    pdf_filename = os.path.splitext(md_filename)[0] + ".pdf"
    pdf_path = os.path.join(OUTPUT_PDF_DIR, pdf_filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=1.45 * inch,
        bottomMargin=0.75 * inch,
        title=topic,
    )

    def _add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#687076"))
        canvas.drawRightString(document.pagesize[0] - 0.75 * inch, 0.45 * inch, f"Page {document.page}")
        canvas.drawString(0.75 * inch, 0.45 * inch, "Notes Generator")
        canvas.restoreState()

    doc.build(
        _story_from_markdown(md_text, theme),
        onFirstPage=lambda c, d: (_cover_page(c, d, theme, topic), _add_page_number(c, d)),
        onLaterPages=_add_page_number,
    )
    print(f"  {md_filename} -> {pdf_path}")
    return True


def main():
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        if not os.path.isdir(OUTPUT_MD_DIR):
            print(f"No {OUTPUT_MD_DIR}/ directory found. Run generate_notes.py first.")
            return
        targets = [f for f in os.listdir(OUTPUT_MD_DIR) if f.endswith(".md")]

    if not targets:
        print("No markdown files to convert.")
        return

    print(f"Converting {len(targets)} file(s) to PDF...")
    ok, failed = 0, 0
    for filename in targets:
        try:
            if convert_file(filename):
                ok += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  FAILED: {filename} — {e}", file=sys.stderr)
            failed += 1

    print(f"\nDone: {ok} succeeded, {failed} failed.")


if __name__ == "__main__":
    main()
