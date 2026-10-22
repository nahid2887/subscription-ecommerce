from rest_framework import serializers
from django.contrib.auth.models import User
from drf_spectacular.utils import extend_schema_field
from .models import TermsAndConditions


class TermsAuditUserSerializer(serializers.ModelSerializer):
    """
    Minimal representation of the super admin user who authored or updated the terms.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = fields


class TermsAndConditionsSerializer(serializers.ModelSerializer):
    """
    Full serializer for reading Terms and Conditions data.
    """
    created_by = TermsAuditUserSerializer(read_only=True)
    updated_by = TermsAuditUserSerializer(read_only=True)

    class Meta:
        model = TermsAndConditions
        fields = [
            'id',
            'title',
            'content',
            'version',
            'is_active',
            'effective_date',
            'created_at',
            'updated_at',
            'created_by',
            'updated_by',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class TermsAndConditionsCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer used by Super Admin to create or edit Terms and Conditions.
    """
    title = serializers.CharField(
        max_length=255,
        required=False,
        default='Terms and Conditions',
        help_text="Title of the terms and conditions agreement."
    )
    content = serializers.CharField(
        help_text="Full text content of the terms and conditions (supports plain text, Markdown, or HTML)."
    )
    version = serializers.CharField(
        max_length=50,
        required=False,
        default='1.0',
        help_text="Version label, e.g. '1.0' or '2026.1'."
    )
    is_active = serializers.BooleanField(
        required=False,
        default=True,
        help_text="If set to true, this becomes the primary active version shown across the store."
    )
    effective_date = serializers.DateTimeField(
        required=False,
        help_text="Optional datetime when these terms become legally active (defaults to current time)."
    )

    class Meta:
        model = TermsAndConditions
        fields = [
            'title',
            'content',
            'version',
            'is_active',
            'effective_date',
        ]


class TermsMessageResponseSerializer(serializers.Serializer):
    """
    Standard message response for actions such as deletion.
    """
    detail = serializers.CharField(help_text="Status or confirmation message.")
