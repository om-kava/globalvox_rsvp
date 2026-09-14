from rest_framework import serializers
from apps.invitees.models import Invitee

class InviteeSerializer(serializers.ModelSerializer):
    """
    Serializer for Invitee records with masked phone privacy representation.
    """
    phone_masked = serializers.CharField(read_only=True)

    class Meta:
        model = Invitee
        fields = ['id', 'external_id', 'name', 'phone', 'phone_masked', 'email', 'created_at']
        read_only_fields = ['id', 'phone_masked', 'created_at']

class CSVUploadSerializer(serializers.Serializer):
    """
    Validates uploaded multipart file and preview flag.
    """
    file = serializers.FileField(required=True)
    preview_only = serializers.BooleanField(default=False, required=False)

    def validate_file(self, value):
        filename = value.name.lower()
        if not filename.endswith('.csv'):
            raise serializers.ValidationError("Only .csv files are supported. Please upload a standard CSV file.")

        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(f"File size cannot exceed 10MB (uploaded: {round(value.size / (1024*1024), 2)}MB).")

        return value
