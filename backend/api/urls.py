# backend/api/urls.py
from django.urls import path

from .views import (
    UploadDatasetView,
    DatasetSummaryView,
    DatasetHistoryView
)
from .report_view import dataset_report_weasy

urlpatterns = [
    path("datasets/upload/", UploadDatasetView.as_view(), name="upload-dataset"),
    path("datasets/<int:pk>/summary/", DatasetSummaryView.as_view(), name="dataset-summary"),
    path("datasets/history/", DatasetHistoryView.as_view(), name="dataset-history"),

    # NEW: WeasyPrint report
    path("datasets/<int:pk>/report/", dataset_report_weasy, name="dataset-report"),
]
