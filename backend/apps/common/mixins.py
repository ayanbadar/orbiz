"""View mixins shared by the store-scoped CRUD apps (products, orders, customers)."""

from rest_framework import status
from rest_framework.response import Response

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH"})


class WritesThrottleOnPostMixin:
    """Throttle POST with the `writes` scope; reads on the same view stay unthrottled."""

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "writes"
            return super().get_throttles()
        return []


class InputOutputSerializerMixin:
    """
    Separate request and response contracts on generic create/update views.

    - `serializer_class` shapes reads (GET).
    - `input_serializer_class` validates and saves writes (POST/PUT/PATCH).
    - `output_serializer_class` shapes the write response; defaults to `serializer_class`.

    The response re-reads the saved row through `get_queryset()`, so it carries the
    same annotations and prefetches as a GET of that object.
    """

    input_serializer_class = None
    output_serializer_class = None

    def get_serializer_class(self):
        if self.request.method in WRITE_METHODS:
            return self.input_serializer_class
        return super().get_serializer_class()

    def get_output_serializer_class(self):
        return self.output_serializer_class or self.serializer_class

    def get_output_instance(self, instance):
        return self.get_queryset().get(pk=instance.pk)

    def get_output_data(self, instance):
        serializer_class = self.get_output_serializer_class()
        return serializer_class(self.get_output_instance(instance)).data

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.get_output_data(instance), status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.get_output_data(instance))
