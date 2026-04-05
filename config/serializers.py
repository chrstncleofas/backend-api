from rest_framework import serializers


class FileUploadSerializer(serializers.Serializer):
    """Single file upload."""
    file = serializers.FileField()


class MultiFileUploadSerializer(serializers.Serializer):
    """Multiple file upload (1–10 files)."""
    files = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=10,
    )
