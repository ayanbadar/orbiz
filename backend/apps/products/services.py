from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction

from apps.common.exceptions import ConflictError
from apps.products.models import InventoryAdjustment, Product


def sanitize_image_url(url: str | None) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    try:
        URLValidator()(value)
    except ValidationError:
        return ""
    return value[:200]


@transaction.atomic
def create_product(*, store, **fields) -> Product:
    image_url = sanitize_image_url(fields.pop("image_url", ""))
    try:
        return Product.objects.create(
            store=store,
            currency=store.currency,
            image_url=image_url,
            **fields,
        )
    except IntegrityError as exc:
        raise ConflictError("A product with this SKU already exists in this store.") from exc


@transaction.atomic
def update_product(*, product: Product, **fields) -> Product:
    if "image_url" in fields:
        fields["image_url"] = sanitize_image_url(fields["image_url"])
    for key, value in fields.items():
        setattr(product, key, value)
    try:
        product.save()
    except IntegrityError as exc:
        raise ConflictError("A product with this SKU already exists in this store.") from exc
    return product


@transaction.atomic
def deactivate_product(*, product: Product) -> Product:
    product.is_active = False
    product.save(update_fields=["is_active", "updated_at"])
    return product


@transaction.atomic
def adjust_stock(*, product: Product, delta: int, reason: str, user) -> InventoryAdjustment:
    locked = Product.objects.select_for_update().get(pk=product.pk)
    before = locked.stock_quantity
    after = before + delta
    if after < 0:
        raise ValidationError({"delta": "Stock cannot go below zero."})
    locked.stock_quantity = after
    locked.save(update_fields=["stock_quantity", "updated_at"])
    return InventoryAdjustment.objects.create(
        product=locked,
        delta=delta,
        quantity_before=before,
        quantity_after=after,
        reason=reason.strip(),
        created_by=user,
    )


@transaction.atomic
def import_product_from_channel3(
    *,
    store,
    channel3_product_id: str,
    sku: str,
    price,
    stock_quantity: int,
    low_stock_threshold: int,
    channel3_payload: dict,
) -> Product:
    existing = (
        Product.objects.select_for_update()
        .filter(store=store, channel3_product_id=channel3_product_id)
        .exclude(channel3_product_id="")
        .first()
    )
    if existing:
        raise ConflictError(
            f"This Channel3 product is already imported as SKU {existing.sku}.",
            extra={"existing_id": existing.pk, "existing_sku": existing.sku},
        )
    if Product.objects.filter(store=store, sku=sku).exists():
        raise ConflictError("A product with this SKU already exists in this store.")

    title = (channel3_payload.get("title") or "").strip() or sku
    description = channel3_payload.get("description") or ""
    image_url = sanitize_image_url(channel3_payload.get("image_url") or "")
    currency = (channel3_payload.get("currency") or store.currency or "USD").upper()[:3]

    try:
        return Product.objects.create(
            store=store,
            name=title[:255],
            sku=sku,
            description=description,
            price=price,
            currency=currency,
            stock_quantity=stock_quantity,
            low_stock_threshold=low_stock_threshold,
            image_url=image_url,
            channel3_product_id=channel3_product_id,
            channel3_source=channel3_payload,
            is_active=True,
        )
    except IntegrityError as exc:
        raise ConflictError("Could not import product due to a catalog conflict.") from exc
