# api/serializers.py
from rest_framework import serializers
from .models import Dataset

class DatasetUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    class Meta:
        model = Dataset
        fields = ("id", "file", "original_filename")

    def create(self, validated_data):
        request = self.context.get("request")
        owner = request.user
        f = validated_data.pop("file")
        original_filename = f.name
        ds = Dataset.objects.create(owner=owner, file=f, original_filename=original_filename)
        return ds

class DatasetListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = ("id", "original_filename", "file", "uploaded_at", "summary_json")
