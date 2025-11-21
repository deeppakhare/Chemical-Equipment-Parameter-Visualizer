# api/admin.py
from django.contrib import admin
from .models import Dataset

@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "original_filename", "uploaded_at")
    readonly_fields = ("uploaded_at",)
