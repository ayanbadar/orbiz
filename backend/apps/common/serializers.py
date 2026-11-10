from rest_framework import serializers


class ErrorEnvelopeSerializer(serializers.Serializer):
    """Documented shape for ApplicationError responses (detail + optional code)."""

    detail = serializers.CharField()
    code = serializers.CharField(required=False)


def require_nonempty_name(value: str, *, message: str = "Enter a name.") -> str:
    """Shared trim + required name validation for create/update serializers."""
    name = (value or "").strip()
    if not name:
        raise serializers.ValidationError(message)
    return name
