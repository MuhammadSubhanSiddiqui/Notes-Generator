"""
Converts every .md in output/md/ to a styled .pdf in output/pdf/.

Requires (install once, locally):
    pip install weasyprint markdown
    (weasyprint needs system libs on some OSes — see README.md troubleshooting)

Usage:
    python convert_to_pdf.py                 # converts all files in output/md/
    python convert_to_pdf.py react-js.md      # converts just one file
"""

import os
import sys
import markdown
from weasyprint import HTML

from config import OUTPUT_MD_DIR, OUTPUT_PDF_DIR

CSS_PATH = os.path.join("templates", "notes_style.css")

HTML_WRAPPER = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
{body}
</body>
</html>"""


def convert_file(md_filename: str):
    md_path = os.path.join(OUTPUT_MD_DIR, md_filename)
    if not os.path.exists(md_path):
        print(f"  Skipping — not found: {md_path}")
        return False

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    html_body = markdown.markdown(
        md_text,
        extensions=["fenced_code", "tables", "codehilite", "toc"],
    )
    full_html = HTML_WRAPPER.format(body=html_body)

    os.makedirs(OUTPUT_PDF_DIR, exist_ok=True)
    pdf_filename = os.path.splitext(md_filename)[0] + ".pdf"
    pdf_path = os.path.join(OUTPUT_PDF_DIR, pdf_filename)

    HTML(string=full_html, base_url=".").write_pdf(pdf_path, stylesheets=[CSS_PATH])
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
