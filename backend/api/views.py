# api/views.py
import os
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.views import APIView
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from .models import Dataset
from .serializers import DatasetUploadSerializer, DatasetListSerializer
from .utils import compute_summary_from_csv_file

# helper: keep last 5 datasets per user
def rotate_user_datasets(owner, keep=5):
    qs = Dataset.objects.filter(owner=owner).order_by("-uploaded_at")
    ids = list(qs.values_list("id", flat=True))
    if len(ids) > keep:
        to_delete = ids[keep:]
        for pk in to_delete:
            try:
                ds = Dataset.objects.get(pk=pk)
                # remove file
                if ds.file and os.path.exists(ds.file.path):
                    os.remove(ds.file.path)
                ds.delete()
            except Dataset.DoesNotExist:
                pass

class UploadDatasetView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, format=None):
        serializer = DatasetUploadSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            ds = serializer.save()
            # compute summary immediately and save to model
            try:
                path = ds.file.path
                summary = compute_summary_from_csv_file(path)
                ds.summary_json = summary
                ds.save()
            except Exception as e:
                # do not fail upload if compute fails, but return note
                ds.summary_json = {"error": f"summary failed: {str(e)}"}
                ds.save()
            # rotate user's datasets to keep last 5
            rotate_user_datasets(request.user, keep=5)
            return Response({
                "dataset_id": ds.id,
                "summary_url": f"/api/datasets/{ds.id}/summary/",
                "history_url": "/api/datasets/history/"
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DatasetSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, format=None):
        ds = get_object_or_404(Dataset, pk=pk, owner=request.user)
        # If summary_json exists, return it; else compute from file
        if ds.summary_json:
            return Response({"dataset_id": ds.id, **ds.summary_json})
        if not ds.file:
            return Response({"error": "file missing"}, status=status.HTTP_404_NOT_FOUND)
        path = ds.file.path
        try:
            summary = compute_summary_from_csv_file(path)
            ds.summary_json = summary
            ds.save()
            return Response({"dataset_id": ds.id, **summary})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DatasetHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        qs = Dataset.objects.filter(owner=request.user).order_by("-uploaded_at")[:5]
        ser = DatasetListSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)


# Simple PDF generation stub using reportlab
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
def generate_simple_pdf(path, summary_payload):
    c = canvas.Canvas(path, pagesize=letter)
    text = c.beginText(40, 750)
    text.setFont("Helvetica", 12)
    text.textLine("Dataset Report")
    text.textLine("")
    text.textLine(f"Dataset ID: {summary_payload.get('dataset_id')}")
    text.textLine(f"Rows: {summary_payload.get('rows')}")
    text.textLine("")
    text.textLine("Summary (numeric columns):")
    for col, stats in (summary_payload.get("summary") or {}).items():
        text.textLine(f"- {col}: mean={stats.get('mean')}, min={stats.get('min')}, max={stats.get('max')}")
    c.drawText(text)
    c.showPage()
    c.save()

class DatasetReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, format=None):
        ds = get_object_or_404(Dataset, pk=pk, owner=request.user)
        # ensure summary exists
        if not ds.summary_json:
            if ds.file and os.path.exists(ds.file.path):
                ds.summary_json = compute_summary_from_csv_file(ds.file.path)
                ds.save()
            else:
                return Response({"error": "no summary and file missing"}, status=404)
        tmp_dir = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(tmp_dir, exist_ok=True)
        out_path = os.path.join(tmp_dir, f"report_{ds.id}.pdf")
        generate_simple_pdf(out_path, {"dataset_id": ds.id, **ds.summary_json})
        if os.path.exists(out_path):
            return FileResponse(open(out_path, "rb"), filename=f"report_{ds.id}.pdf", as_attachment=True)
        raise Http404("report generation failed")
