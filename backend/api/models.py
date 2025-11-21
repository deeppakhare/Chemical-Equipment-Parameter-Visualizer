# api/models.py
import os
import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

def dataset_upload_path(instance, filename):
    # store in media/datasets/<user_id>/<unique-filename>
    ext = filename.split(".")[-1]
    fn = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join("datasets", str(instance.owner.id), fn)

class Dataset(models.Model):
    """
    Represents an uploaded dataset (CSV).
    We'll store metadata and a pointer to the raw CSV file.
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="datasets")
    file = models.FileField(upload_to=dataset_upload_path)
    original_filename = models.CharField(max_length=256, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # basic cached summary JSON (so we don't recompute for every request)
    summary_json = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.original_filename or self.file.name} ({self.owner})"
