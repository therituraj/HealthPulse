"""PDF export of a report (reportlab)."""
from io import BytesIO
from xml.sax.saxutils import escape

from .health import RESULT_TEXT

ACCENT = "#ff574d"
INK = "#292929"


def build_report_pdf(report, patient_name, sections):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    accent, ink = colors.HexColor(ACCENT), colors.HexColor(INK)
    grey, line = colors.HexColor("#666666"), colors.HexColor("#dddddd")
    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=ink, spaceAfter=4)
    h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=ink, spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14, textColor=ink)
    small = ParagraphStyle("small", fontName="Helvetica", fontSize=8.5, leading=12, textColor=grey)
    brand = ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=11, textColor=accent, spaceAfter=10)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=20 * mm, title=report.title, author="HealthPulse")
    story = [Paragraph("HealthPulse", brand), Paragraph(escape(report.title), h1)]

    meta = [
        ["Report ID", report.public_id.upper(), "Patient", escape(patient_name or "-")],
        ["Generated", report.created_at.strftime("%d %b %Y, %H:%M UTC"), "Type",
         "Diabetes" if report.kind == "diabetes" else "Heart disease"],
    ]
    meta_t = Table([[Paragraph(str(c), body) for c in row] for row in meta], colWidths=[26 * mm, 62 * mm, 22 * mm, 64 * mm])
    meta_t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                                ("TOPPADDING", (0, 0), (-1, -1), 3), ("LINEBELOW", (0, -1), (-1, -1), 0.5, line)]))
    story += [meta_t, Spacer(1, 10)]

    high = report.is_high_risk
    headline = RESULT_TEXT[report.kind][0 if high else 1]
    prob = f" Estimated probability: {report.percent:g}%." if report.percent is not None else ""
    result = Table([[Paragraph(f"<b>{escape(headline)}</b><br/>This is an estimate from a machine learning "
                               f"model, not a diagnosis.{prob}", body)]], colWidths=[174 * mm])
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff0ee" if high else "#ecf8f0")),
        ("LINEBEFORE", (0, 0), (0, -1), 4, accent if high else colors.HexColor("#2e9e5b")),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    story.append(result)

    for title, rows in sections:
        story.append(Paragraph(escape(title), h2))
        t = Table([[Paragraph(escape(a), body), Paragraph(f"<b>{escape(b)}</b>", body)] for a, b in rows],
                  colWidths=[85 * mm, 89 * mm])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, line), ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#faf7f6")]),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
        story.append(t)

    story += [Spacer(1, 14), Paragraph("HealthPulse gives an estimate for information only. It does not replace "
                                       "professional medical advice. Please talk to a doctor about your result.", small)]

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(grey)
        canvas.drawString(18 * mm, 10 * mm, f"HealthPulse | {report.public_id.upper()}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
