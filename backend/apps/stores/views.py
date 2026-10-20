from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stores.permissions import IsStoreOwner
from apps.stores.serializers import (
    SetDefaultStoreSerializer,
    StoreCreateSerializer,
    StoreSerializer,
    StoreUpdateSerializer,
)
from apps.stores.services import get_default_store, user_stores_queryset


class StoreListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StoreCreateSerializer
        return StoreSerializer

    def get_queryset(self):
        return user_stores_queryset(self.request.user)

    @extend_schema(tags=["stores"], summary="List my stores", responses=StoreSerializer(many=True))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["stores"],
        summary="Create a store workspace",
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
            return [IsAuthenticated(), IsStoreOwner()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return user_stores_queryset(self.request.user)

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

    @extend_schema(tags=["stores"], summary="Current default store", responses=StoreSerializer)
    def get(self, request):
        store = get_default_store(request.user)
        if store is None:
            return Response({"detail": "No store workspace yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(StoreSerializer(store, context={"request": request}).data)


class SetDefaultStoreView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["stores"],
        summary="Set default store",
        request=SetDefaultStoreSerializer,
        responses=StoreSerializer,
    )
    def post(self, request):
        serializer = SetDefaultStoreSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        store = serializer.save()
        return Response(StoreSerializer(store, context={"request": request}).data)


def resolve_request_store(request):
    """Attach the caller's default store onto the request for product views."""
    store = get_default_store(request.user)
    request.store = store
    return store
