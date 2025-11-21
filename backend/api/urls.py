# api/urls.py
from django.urls import path
from .views import UploadDatasetView, DatasetSummaryView, DatasetHistoryView, DatasetReportView

urlpatterns = [
    path("datasets/upload/", UploadDatasetView.as_view(), name="upload-dataset"),
    path("datasets/<int:pk>/summary/", DatasetSummaryView.as_view(), name="dataset-summary"),
    path("datasets/history/", DatasetHistoryView.as_view(), name="dataset-history"),
    path("datasets/<int:pk>/report/", DatasetReportView.as_view(), name="dataset-report"),
]
