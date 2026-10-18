"""Single translation point: domain + Django errors → HTTP responses."""

from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.common.exceptions import ApplicationError

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            exc = exceptions.ValidationError(exc.message_dict)
        else:
            exc = exceptions.ValidationError(list(exc.messages))

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()

    if isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, ApplicationError):
        path = context["request"].path if context.get("request") is not None else "?"
        logger.warning("ApplicationError on %s: %s", path, exc.message)
        body = {"detail": exc.message, "code": exc.code}
        body.update({k: v for k, v in exc.extra.items() if v is not None})
        return Response(body, status=exc.status_code)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    # Keep DRF field-error shape for clients; attach a stable code when possible.
    if isinstance(response.data, dict) and "code" not in response.data:
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            response.data = {**response.data}
        elif "detail" in response.data and isinstance(response.data["detail"], str):
            response.data = {
                **response.data,
                "code": _code_for_status(response.status_code),
            }
    return response


def _code_for_status(status_code: int) -> str:
    return {
        401: "authentication_failed",
        403: "permission_denied",
        404: "not_found",
        429: "throttled",
    }.get(status_code, "error")
