from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.models import User
from apps.accounts.serializers import (
    AuthTokenResponseSerializer,
    ChangePasswordSerializer,
    DetailSerializer,
    ForgotPasswordResponseSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    UserSerializer,
)
from apps.accounts.services import (
    FORGOT_PASSWORD_MESSAGE,
    INVALID_CREDENTIALS_MESSAGE,
    blacklist_refresh_tokens,
    issue_tokens,
    send_password_reset_email,
)


class PublicAPIView(APIView):
    """Open to anonymous clients. JWT auth stays enabled so a bad login is a 401."""

    permission_classes = [AllowAny]


class RegisterView(PublicAPIView):
    throttle_scope = "auth"

    @extend_schema(
        tags=["auth"],
        summary="Create an account",
        request=RegisterSerializer,
        responses={201: AuthTokenResponseSerializer, 400: DetailSerializer},
        auth=[],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(_token_payload(user), status=status.HTTP_201_CREATED)


class LoginView(PublicAPIView):
    throttle_scope = "auth"

    @extend_schema(
        tags=["auth"],
        summary="Sign in",
        request=LoginSerializer,
        responses={200: AuthTokenResponseSerializer, 401: DetailSerializer},
        auth=[],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            raise AuthenticationFailed(INVALID_CREDENTIALS_MESSAGE)
        update_last_login(None, user)
        return Response(_token_payload(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth"

    @extend_schema(
        tags=["auth"],
        summary="Sign out",
        request=LogoutSerializer,
        responses={204: None, 400: DetailSerializer},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
        except TokenError:
            return Response(
                {"detail": "Refresh token is invalid or expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if int(token.get("user_id")) != request.user.id:
            return Response(
                {"detail": "Refresh token does not belong to this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            token.blacklist()
        except TokenError:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RefreshView(TokenRefreshView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "auth"

    @extend_schema(tags=["auth"], summary="Refresh access token", auth=[])
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], summary="Current account", responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(
        tags=["auth"],
        summary="Update profile",
        request=ProfileUpdateSerializer,
        responses={200: UserSerializer},
    )
    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "password"

    @extend_schema(
        tags=["auth"],
        summary="Change password",
        request=ChangePasswordSerializer,
        responses={204: None, 400: DetailSerializer},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        blacklist_refresh_tokens(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ForgotPasswordView(PublicAPIView):
    throttle_scope = "password"

    @extend_schema(
        tags=["auth"],
        summary="Request a password reset",
        request=ForgotPasswordSerializer,
        responses={200: ForgotPasswordResponseSerializer},
        auth=[],
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        reset_url = None
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            user = None
        if user is not None:
            reset_url = send_password_reset_email(user)
        payload = {"message": FORGOT_PASSWORD_MESSAGE}
        if settings.DEBUG and reset_url:
            payload["debug_reset_url"] = reset_url
        return Response(payload)


class ResetPasswordView(PublicAPIView):
    throttle_scope = "password"

    @extend_schema(
        tags=["auth"],
        summary="Set a new password from a reset link",
        request=ResetPasswordSerializer,
        responses={204: None, 400: DetailSerializer},
        auth=[],
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        blacklist_refresh_tokens(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _token_payload(user: User) -> dict:
    return {**issue_tokens(user), "user": UserSerializer(user).data}
