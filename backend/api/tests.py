# api/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from api.models import Dataset
import os
User = get_user_model()

class ApiSmokeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tuser", password="tpass")
        self.client = APIClient()
        self.client.login(username="tuser", password="tpass")

    def test_history_empty(self):
        resp = self.client.get(reverse("dataset-history"))
        assert resp.status_code == 200
        self.assertEqual(len(resp.json()), 0)

    def test_upload_and_summary(self):
        # use sample file from /mnt/data if available
        sample = "/mnt/data/sample_equipment_data.csv"
        if os.path.exists(sample):
            with open(sample, "rb") as f:
                resp = self.client.post(reverse("upload-dataset"), {"file": f}, format="multipart")
                self.assertEqual(resp.status_code, 201)
                data = resp.json()
                ds_id = data["dataset_id"]
                # get summary
                resp2 = self.client.get(f"/api/datasets/{ds_id}/summary/")
                self.assertEqual(resp2.status_code, 200)
                summary = resp2.json()
                self.assertIn("numeric_columns", summary)
        else:
            self.skipTest("sample file not present")
