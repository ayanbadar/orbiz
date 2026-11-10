"""Shared list pagination for store-scoped APIs (products, orders, …)."""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    PageNumberPagination with an optional client `page_size`.

    Default size matches REST_FRAMEWORK["PAGE_SIZE"]. Clients may pass
    `?page_size=` up to max_page_size — reuse this class instead of per-app
    pagination subclasses.
    """

    page_size_query_param = "page_size"
    max_page_size = 100
