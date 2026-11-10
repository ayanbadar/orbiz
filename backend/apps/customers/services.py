from django.db import transaction

from apps.customers.models import Customer


@transaction.atomic
def create_customer(*, store, name: str, email: str = "", phone: str = "", notes: str = "") -> Customer:
    return Customer.objects.create(
        store=store,
        name=name.strip(),
        email=(email or "").strip(),
        phone=(phone or "").strip(),
        notes=(notes or "").strip(),
    )


@transaction.atomic
def update_customer(*, customer: Customer, **fields) -> Customer:
    if "name" in fields and fields["name"] is not None:
        fields["name"] = fields["name"].strip()
    for key in ("email", "phone", "notes"):
        if key in fields and fields[key] is not None:
            fields[key] = fields[key].strip()
    for key, value in fields.items():
        setattr(customer, key, value)
    customer.save()
    return customer
