from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction

from apps.common.exceptions import ConflictError
from apps.products.models import InventoryAdjustment, Product


# Matches Product.image_url max_length — leave room for S3/CloudFront query strings.
IMAGE_URL_MAX_LENGTH = 2048


def sanitize_image_url(url: str | None) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    try:
        URLValidator(schemes=["http", "https"])(value)
    except ValidationError:
        return ""
    return value[:IMAGE_URL_MAX_LENGTH]


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


def check_stock(*, product: Product, quantity: int) -> dict:
    """
    Read-only pre-check that `quantity` could be sold right now.

    This is NOT a stock reservation. §2.4 Orders must still lock the product
    (`select_for_update`), re-validate, and deduct in the same transaction as
    the order line — otherwise concurrent check-then-buy can oversell.
    """
    if quantity < 1:
        raise ValidationError({"quantity": "Quantity must be at least 1."})
    if not product.is_active:
        raise ValidationError({"detail": "This product is inactive and cannot be sold."})
    if product.stock_quantity < quantity:
        raise ValidationError(
            {
                "quantity": (
                    f"Insufficient stock. Only {product.stock_quantity} available."
                )
            }
        )
    return {
        "product_id": product.pk,
        "sku": product.sku,
        "requested_quantity": quantity,
        "stock_quantity": product.stock_quantity,
        "available": True,
    }


@transaction.atomic
def adjust_stock(
    *,
    product: Product,
    delta: int,
    reason: str,
    user,
    already_locked: bool = False,
) -> InventoryAdjustment:
    """
    Mutate stock and write an InventoryAdjustment.

    Pass already_locked=True when the caller holds select_for_update on this
    product in the same transaction (e.g. order confirm/cancel) so we do not
    re-lock and nest an extra savepoint.
    """
    locked = (
        product
        if already_locked
        else Product.objects.select_for_update().get(pk=product.pk)
    )
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
