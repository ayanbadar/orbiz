from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stores.models import Store
from apps.stores.permissions import IsStoreAdmin
from apps.stores.serializers import (
    StoreCreateSerializer,
    StoreSerializer,
    StoreUpdateSerializer,
)
from apps.stores.services import get_user_store


class StoreListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StoreCreateSerializer
        return StoreSerializer

    def get_queryset(self):
        return Store.objects.filter(memberships__user=self.request.user)

    @extend_schema(tags=["stores"], summary="Get my store (0 or 1)", responses=StoreSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["stores"],
        summary="Create my store (one per user)",
        request=StoreCreateSerializer,
        responses={201: StoreSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        store = serializer.save()
        return Response(
            StoreSerializer(store, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class StoreDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsStoreAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return Store.objects.filter(memberships__user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return StoreUpdateSerializer
        return StoreSerializer

    @extend_schema(tags=["stores"], summary="Get store", responses=StoreSerializer)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["stores"],
        summary="Update store",
        request=StoreUpdateSerializer,
        responses=StoreSerializer,
    )
    def patch(self, request, *args, **kwargs):
        response = super().patch(request, *args, **kwargs)
        store = self.get_object()
        response.data = StoreSerializer(store, context={"request": request}).data
        return response


class StoreMeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["stores"], summary="My store", responses=StoreSerializer)
    def get(self, request):
        store = get_user_store(request.user)
        if store is None:
            return Response({"detail": "No store workspace yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(StoreSerializer(store, context={"request": request}).data)
