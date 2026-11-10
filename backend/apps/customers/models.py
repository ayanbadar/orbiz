from django.db import models

from apps.stores.models import Store


class Customer(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=64, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["store", "name"]),
        ]

    def __str__(self) -> str:
        return self.name
