from rest_framework import serializers


class ErrorEnvelopeSerializer(serializers.Serializer):
    """Documented shape for ApplicationError responses (detail + optional code)."""

    detail = serializers.CharField()
    code = serializers.CharField(required=False)
