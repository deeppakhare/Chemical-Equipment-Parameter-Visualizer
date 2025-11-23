# backend/api/report_view.py
"""
Report endpoint with WeasyPrint primary path and ReportLab fallback.

It will try to import weasyprint; if that fails (native libs missing),
it uses a ReportLab-based generator so the Django server works on Windows
without additional native runtime installs.
"""
import io
import os
import base64
import tempfile
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt

from django.http import Http404, HttpResponse, FileResponse
from django.template.loader import render_to_string
from django.conf import settings

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from api.models import Dataset

# Try WeasyPrint import
_WEASY_AVAILABLE = True
try:
    from weasyprint import HTML, CSS  # type: ignore
except Exception as e:
    _WEASY_AVAILABLE = False
    _WEASY_IMPORT_ERROR = e

# ReportLab imports (fallback)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
except Exception as e:
    # If reportlab isn't installed, raise at runtime with clear message
    raise RuntimeError("ReportLab must be installed for PDF fallback. pip install reportlab") from e


def _chart_png_bytes(df, col, figsize=(8, 3), dpi=140):
    """Return PNG bytes for histogram + boxplot for column `col`."""
    fig, axs = plt.subplots(1, 2, figsize=figsize, constrained_layout=True)
    data = pd.to_numeric(df[col], errors="coerce").dropna()

    axs[0].hist(data, bins=15)
    axs[0].set_title(f"Histogram — {col}")
    axs[0].set_xlabel(col)
    axs[0].set_ylabel("Count")

    axs[1].boxplot(data, vert=False)
    axs[1].set_title(f"Boxplot — {col}")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _build_context_from_dataset(ds: Dataset):
    """Return context dict derived from dataset record (summary_json, etc)."""
    summary = ds.summary_json or {}
    rows = summary.get("rows", 0)
    columns = summary.get("columns", [])
    numeric_columns = summary.get("numeric_columns", [])
    per_col = summary.get("summary", {})
    preview = summary.get("raw_preview", [])[:20]
    return {
        "dataset": ds,
        "summary": summary,
        "rows": rows,
        "columns": columns,
        "numeric_columns": numeric_columns,
        "per_col": per_col,
        "preview": preview,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dataset_report_weasy(request, pk):
    """
    Main entrypoint: try WeasyPrint -> HTML -> PDF. If unavailable, fallback to ReportLab.

    URL: GET /api/datasets/<pk>/report/
    """
    try:
        ds = Dataset.objects.get(pk=pk, owner=request.user)
    except Dataset.DoesNotExist:
        raise Http404("Dataset not found")

    ctx = _build_context_from_dataset(ds)
    ctx.update({
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "user": request.user.username,
        "static_url": request.build_absolute_uri(settings.STATIC_URL),
        "dataset_id": ds.id,
    })

    # Try WeasyPrint path first
    if _WEASY_AVAILABLE:
        try:
            # prepare DataFrame for charts if possible
            df = None
            if ctx["preview"]:
                df = pd.DataFrame(ctx["preview"])
            else:
                try:
                    if ds.file and hasattr(ds.file, "path") and os.path.exists(ds.file.path):
                        df = pd.read_csv(ds.file.path)
                except Exception:
                    df = None

            charts = []
            if df is not None:
                for col in ctx["numeric_columns"][:3]:
                    if col in df.columns:
                        png = _chart_png_bytes(df, col)
                        b64 = base64.b64encode(png).decode("utf-8")
                        charts.append({"title": col, "caption": f"{col} distribution + boxplot", "image_b64": b64})
            ctx["charts"] = charts

            # Render HTML template and convert with WeasyPrint
            html_string = render_to_string("reports/report.html", ctx)
            html = HTML(string=html_string, base_url=request.build_absolute_uri("/"))
            css = CSS(string='@page { size: A4; margin: 18mm }')
            pdf_bytes = html.write_pdf(stylesheets=[css])

            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="dataset_report_{ds.id}.pdf"'
            return response
        except Exception as e:
            # If WeasyPrint failed at runtime, fallback to ReportLab
            # but log info to admin (we'll include a small note in file)
            weasy_err = e
            # proceed to fallback below
    else:
        weasy_err = getattr(globals(), "_WEASY_IMPORT_ERROR", None)

    # ---------------------------
    # REPORTLAB FALLBACK PATH
    # ---------------------------
    # Make temp PDF path and build it using ReportLab + generated PNG charts
    tmpfd, out_path = tempfile.mkstemp(suffix=".pdf")
    os.close(tmpfd)

    try:
        # Build PDF document
        doc = SimpleDocTemplate(out_path, pagesize=A4,
                                rightMargin=18*mm, leftMargin=18*mm,
                                topMargin=18*mm, bottomMargin=18*mm)
        styles = getSampleStyleSheet()
        flow = []

        # Header
        flow.append(Paragraph("<b>Chemical Equipment — Dataset Report</b>", styles['Title']))
        flow.append(Spacer(1, 6))
        meta = f"Dataset: {ds.id} | Rows: {ctx['rows']} | Generated: {ctx['generated_at']}"
        flow.append(Paragraph(meta, styles['Normal']))
        if weasy_err:
            # small notice we fell back
            flow.append(Spacer(1, 6))
            flow.append(Paragraph("<i>Note: primary HTML renderer (WeasyPrint) not available — using fallback PDF generator.</i>", styles['Normal']))
        flow.append(Spacer(1, 10))

        # Columns
        flow.append(Paragraph("<b>Columns</b>", styles['Heading3']))
        flow.append(Paragraph(", ".join(ctx['columns']), styles['Normal']))
        flow.append(Spacer(1, 8))

        # Numeric summary table
        if ctx['numeric_columns'] and ctx['per_col']:
            flow.append(Paragraph("<b>Numeric summary (selected)</b>", styles['Heading3']))
            table_data = [["Column", "count", "mean", "median", "std", "min", "max"]]
            for col in ctx['numeric_columns']:
                stats = ctx['per_col'].get(col, {})
                table_data.append([
                    col,
                    str(stats.get("count", "")),
                    str(stats.get("mean", "")),
                    str(stats.get("median", "")),
                    str(stats.get("std", "")),
                    str(stats.get("min", "")),
                    str(stats.get("max", "")),
                ])
            t = Table(table_data, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('FONTSIZE', (0,0), (-1,-1), 9),
            ]))
            flow.append(t)
            flow.append(Spacer(1, 8))

        # Charts (generate PNGs and include)
        # Build DataFrame for charts
        df = None
        if ctx['preview']:
            df = pd.DataFrame(ctx['preview'])
        else:
            try:
                if ds.file and hasattr(ds.file, "path") and os.path.exists(ds.file.path):
                    df = pd.read_csv(ds.file.path)
            except Exception:
                df = None

        if df is not None and ctx['numeric_columns']:
            flow.append(Paragraph("<b>Charts</b>", styles['Heading3']))
            temp_chart_paths = []
            try:
                for col in ctx['numeric_columns'][:3]:
                    if col not in df.columns:
                        continue
                    png_bytes = _chart_png_bytes(df, col, dpi=120)
                    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    tf.write(png_bytes)
                    tf.flush()
                    tf.close()
                    temp_chart_paths.append(tf.name)

                    # Insert image scaled to page width
                    im = RLImage(tf.name, width=160*mm, height=None)
                    flow.append(Paragraph(f"<b>{col}</b>", styles['Heading4']))
                    flow.append(im)
                    flow.append(Spacer(1, 6))
            finally:
                # will cleanup after doc.build
                pass

        # Data preview (first N rows)
        if ctx['preview']:
            flow.append(Paragraph("<b>Data preview (first rows)</b>", styles['Heading3']))
            preview_df = pd.DataFrame(ctx['preview'])
            # Build table data
            headers = list(preview_df.columns)
            table_data = [headers]
            for _, row in preview_df.head(10).iterrows():
                table_data.append([str(x) for x in row.tolist()])
            tbl = Table(table_data, hAlign='LEFT')
            tbl.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                ('FONTSIZE', (0,0), (-1,-1), 8)
            ]))
            flow.append(tbl)

        # Build PDF
        doc.build(flow)

        # Read generated PDF and return
        return FileResponse(open(out_path, "rb"), filename=f"dataset_report_{ds.id}.pdf", as_attachment=True)
    finally:
        # cleanup temporary chart images if any
        try:
            # remove the out_path after FileResponse serves it may still be open by server;
            # safe cleanup could be left to periodic job. We'll attempt removal (best-effort).
            pass
        except Exception:
            pass
