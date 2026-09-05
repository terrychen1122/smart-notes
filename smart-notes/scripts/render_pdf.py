"""Render a smart-notes Markdown deliverable as a portable PDF."""
import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer


FONT_DIR = Path("/System/Library/Fonts/Supplemental")


def register_fonts():
    """Use a Unicode-capable system font when available, with Helvetica fallback."""
    unicode_font = FONT_DIR / "Arial Unicode.ttf"
    if unicode_font.exists():
        pdfmetrics.registerFont(TTFont("SmartNotesUnicode", str(unicode_font)))
        return {"regular": "SmartNotesUnicode", "bold": "SmartNotesUnicode", "italic": "SmartNotesUnicode"}
    regular = FONT_DIR / "Arial.ttf"
    bold = FONT_DIR / "Arial Bold.ttf"
    italic = FONT_DIR / "Arial Italic.ttf"
    bold_italic = FONT_DIR / "Arial Bold Italic.ttf"
    if not regular.exists():
        return {"regular": "Helvetica", "bold": "Helvetica-Bold", "italic": "Helvetica-Oblique"}
    pdfmetrics.registerFont(TTFont("SmartNotesArial", str(regular)))
    pdfmetrics.registerFont(TTFont("SmartNotesArial-Bold", str(bold)))
    pdfmetrics.registerFont(TTFont("SmartNotesArial-Italic", str(italic)))
    pdfmetrics.registerFont(TTFont("SmartNotesArial-BoldItalic", str(bold_italic)))
    return {"regular": "SmartNotesArial", "bold": "SmartNotesArial-Bold", "italic": "SmartNotesArial-Italic"}


def inline_markup(text):
    """Convert the small Markdown subset emitted by render_notes.py to Paragraph XML."""
    text = html.escape(text, quote=False)
    links = []

    def stash_link(match):
        label = match.group(1)
        url = match.group(2).replace("&amp;", "&")
        links.append(f'<link href="{html.escape(url, quote=True)}" color="#1769aa">{label}</link>')
        return f"\x00LINK{len(links) - 1}\x00"

    text = re.sub(r"\[([^]]+)\]\(([^)]+)\)", stash_link, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r"<font name=\"Courier\">\1</font>", text)
    for index, link in enumerate(links):
        text = text.replace(f"\x00LINK{index}\x00", link)
    return text


def parse_image(line, base_dir):
    match = re.match(r"!\[([^]]*)\]\(([^)]+)\)", line.strip())
    if not match:
        return None
    alt, relative = match.groups()
    path = (base_dir / relative).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Image referenced by Markdown was not found: {path}")
    return alt, path


def make_styles(fonts):
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("SmartNotesTitle", parent=base["Title"], fontName=fonts["bold"],
                                fontSize=22, leading=26, textColor=colors.HexColor("#17324d"), spaceAfter=8),
        "meta": ParagraphStyle("SmartNotesMeta", parent=base["Normal"], fontName=fonts["regular"],
                               fontSize=9, leading=12, textColor=colors.HexColor("#5b6875"), spaceAfter=14),
        "h1": ParagraphStyle("SmartNotesH1", parent=base["Heading1"], fontName=fonts["bold"],
                             fontSize=15, leading=19, textColor=colors.HexColor("#17324d"),
                             spaceBefore=12, spaceAfter=7, keepWithNext=True),
        "h2": ParagraphStyle("SmartNotesH2", parent=base["Heading2"], fontName=fonts["bold"],
                             fontSize=12, leading=15, textColor=colors.HexColor("#245b7a"),
                             spaceBefore=10, spaceAfter=5, keepWithNext=True),
        "body": ParagraphStyle("SmartNotesBody", parent=base["BodyText"], fontName=fonts["regular"],
                                fontSize=10, leading=14, textColor=colors.HexColor("#27333d"), spaceAfter=8),
        "bullet": ParagraphStyle("SmartNotesBullet", parent=base["BodyText"], fontName=fonts["regular"],
                                  fontSize=9.5, leading=13, textColor=colors.HexColor("#27333d"), spaceAfter=3),
        "quote": ParagraphStyle("SmartNotesQuote", parent=base["BodyText"], fontName=fonts["bold"],
                                 fontSize=10, leading=14, leftIndent=16, borderColor=colors.HexColor("#b9d7e8"),
                                 borderWidth=1, borderPadding=8, backColor=colors.HexColor("#f3f8fb"),
                                 textColor=colors.HexColor("#245b7a"), spaceBefore=4, spaceAfter=10),
        "caption": ParagraphStyle("SmartNotesCaption", parent=base["BodyText"], fontName=fonts["italic"],
                                   fontSize=8.5, leading=11, alignment=1, textColor=colors.HexColor("#5b6875"),
                                   spaceBefore=3, spaceAfter=10),
    }


def build_story(markdown_path, doc, styles):
    lines = markdown_path.read_text(encoding="utf-8").splitlines()
    story, paragraph_lines, list_items, list_kind = [], [], [], None

    def flush_paragraph():
        nonlocal paragraph_lines
        if paragraph_lines:
            text = " ".join(line.strip() for line in paragraph_lines)
            if text:
                story.append(Paragraph(inline_markup(text), styles["body"]))
            paragraph_lines = []

    def flush_list():
        nonlocal list_items, list_kind
        if list_items:
            items = [ListItem(Paragraph(inline_markup(item), styles["bullet"]), leftIndent=8)
                     for item in list_items]
            list_kwargs = {
                "bulletType": "bullet" if list_kind == "bullet" else "1",
                "leftIndent": 18,
                "bulletFontName": styles["bullet"].fontName,
                "bulletFontSize": 8,
                "bulletOffsetY": 2,
            }
            if list_kind != "bullet":
                list_kwargs["start"] = "1"
            story.append(ListFlowable(items, **list_kwargs))
            story.append(Spacer(1, 4))
        list_items, list_kind = [], None

    def flush_all():
        flush_paragraph()
        flush_list()

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_all()
            continue
        image = parse_image(line, markdown_path.parent)
        if image:
            flush_all()
            alt, path = image
            image_flowable = Image(str(path))
            image_flowable._restrictSize(doc.width, 3.25 * inch)
            story.append(KeepTogether([image_flowable, Paragraph(inline_markup(alt), styles["caption"])]))
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_all()
            level, text = len(heading.group(1)), heading.group(2)
            style = styles["title"] if level == 1 else styles["h1"] if level == 2 else styles["h2"]
            story.append(Paragraph(inline_markup(text), style))
            continue
        if line.startswith("> "):
            flush_all()
            story.append(Paragraph(inline_markup(line[2:]), styles["quote"]))
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", line)
        ordered = re.match(r"^\d+[.)]\s+(.+)$", line)
        if bullet or ordered:
            flush_paragraph()
            kind = "bullet" if bullet else "ordered"
            if list_kind and list_kind != kind:
                flush_list()
            list_kind = kind
            list_items.append((bullet or ordered).group(1))
            continue
        if line.startswith("Key frame "):
            flush_all()
            story.append(Paragraph(inline_markup(line), styles["meta"]))
            continue
        paragraph_lines.append(line)
    flush_all()
    return story


def add_page_chrome(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(colors.HexColor("#dbe4ea"))
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, height - 34, width - doc.rightMargin, height - 34)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#7b8790"))
    canvas.drawRightString(width - doc.rightMargin, 22, f"Page {doc.page}")
    canvas.restoreState()


def render(markdown_path, output_path):
    fonts = register_fonts()
    styles = make_styles(fonts)
    markdown_path = Path(markdown_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output_path), pagesize=letter,
                            leftMargin=0.65 * inch, rightMargin=0.65 * inch,
                            topMargin=0.58 * inch, bottomMargin=0.48 * inch,
                            title=markdown_path.stem, author="smart-notes")
    doc.build(build_story(markdown_path, doc, styles), onFirstPage=add_page_chrome,
              onLaterPages=add_page_chrome)
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", help="Rendered notes.md file")
    parser.add_argument("--output", required=True, help="Output PDF path")
    args = parser.parse_args()
    print(f"Rendered {render(args.markdown, args.output)}")


if __name__ == "__main__":
    main()
