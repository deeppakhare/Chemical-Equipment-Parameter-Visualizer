# api/management/commands/import_sample.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Dataset
from django.core.files import File
from django.conf import settings
from pathlib import Path
import os

User = get_user_model()

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SAMPLE_PATH = PROJECT_ROOT / "samples" / "sample_equipment_data.csv"
SUMMARY_JSON_PATH = PROJECT_ROOT / "samples" / "sample_summary_api_payload.json" # <-- using your uploaded file path

class Command(BaseCommand):
    help = "Import the provided sample CSV as a dataset for the given username (create user if missing)."

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, default="demo", help="Username to attach the sample dataset to")

    def handle(self, *args, **options):
        username = options["username"]
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password("demo")
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user `{username}` with password 'demo'"))

        if not os.path.exists(SAMPLE_PATH):
            self.stdout.write(self.style.ERROR(f"Sample CSV not found at {SAMPLE_PATH}"))
            return

        with open(SAMPLE_PATH, "rb") as f:
            django_file = File(f)
            ds = Dataset.objects.create(owner=user, original_filename=os.path.basename(SAMPLE_PATH))
            ds.file.save(os.path.basename(SAMPLE_PATH), django_file, save=True)
            # compute summary immediately
            from api.utils import compute_summary_from_csv_file
            try:
                ds.summary_json = compute_summary_from_csv_file(ds.file.path)
                ds.save()
                self.stdout.write(self.style.SUCCESS(f"Imported sample as dataset id={ds.id} for user {username}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Imported file but summary failed: {e}"))
