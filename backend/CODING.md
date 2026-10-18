# Backend coding guide

Build the Orbiz API with the simplest Django REST Framework patterns that stay correct under real use. Prefer one obvious place for each concern over extra layers.

Stack already in the project: Django, Django REST Framework, PostgreSQL, Redis, Celery, `django-environ`. Add a library only when this stack cannot do the job cleanly.

## Where code goes

```text
backend/
├── config/                 # settings, root urls, celery
└── apps/<app_name>/
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── permissions.py      # only when shared across the app
    ├── services.py         # business rules that do not belong in a serializer
    └── tests/
```

Mount product routes under `/api/v1/`. Keep `/health/` as a plain health check. Leave Django admin for internal inspection.

One app per area: accounts, stores, orders, products, customers, payments, assistant. Do not create an app for a single helper.

## Serializers

Every request body and every response goes through a serializer.

- Use `ModelSerializer` when the payload maps to a model.
- Use a plain `Serializer` for actions that are not a model create or update: stock check, checkout, message extraction review, inventory adjustment.
- Declare fields explicitly when the default model fields would leak internal data.
- Put input rules on the serializer: required fields, ranges, choices, cross-field checks.
- Read validated data from `serializer.validated_data`. Do not trust `request.data` in a view.
- Keep serializers focused on shape and validation. Stock deduction, payment capture, and status transitions belong in a service called after `is_valid()`.

```python
class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["customer", "notes", "lines"]

    def validate_lines(self, lines):
        if not lines:
            raise serializers.ValidationError("Add at least one line.")
        return lines
```

Return serializer errors as DRF's default field errors. Do not invent a second error format.

## Views

Use DRF generic views or `ModelViewSet` for ordinary CRUD. Use `APIView` only for an action that is not CRUD, such as creating a PayPal checkout.

A view does four things:

1. Check permission.
2. Validate input with a serializer.
3. Call a model method or a small service.
4. Return a serializer response with the right status code.

```python
class OrderListCreateView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        return Order.objects.filter(store=self.request.user.store).select_related("customer")
```

Querysets are always scoped to the caller's workspace. `get_object()` must 404 for another store's row.

Use `select_related` and `prefetch_related` on list and detail querysets. Paginate list endpoints with DRF page-number pagination.

Wrap multi-row writes in `transaction.atomic()`. Creating an order and reserving stock is one transaction.

## OpenAPI / Swagger

Document the API with `drf-spectacular`. The schema is part of the endpoint, not a follow-up task.

- Add `drf_spectacular` to `INSTALLED_APPS` and set `DEFAULT_SCHEMA_CLASS` to `drf_spectacular.openapi.AutoSchema`.
- Serve Swagger UI and the raw schema from the API, for example `/api/schema/swagger-ui/` and `/api/schema/`.
- Set `extend_schema` when the automatic schema is wrong: action endpoints, webhook receivers, and responses that differ by status code.
- Give each endpoint a short summary, the request serializer, and the response serializer.
- Tag endpoints by app (`orders`, `payments`, `assistant`).
- Keep a Postman collection exported from this schema for the hackathon demo.

If Swagger cannot show an endpoint accurately, fix the schema before calling the endpoint done.

## Rate limiting

Use DRF throttling. The project already caches in Redis, so throttles work across processes. Set `DEFAULT_THROTTLE_CLASSES` and numeric `DEFAULT_THROTTLE_RATES` in `REST_FRAMEWORK`.

Apply a scoped throttle on endpoints that are expensive or easy to abuse:

| Scope | Endpoints |
| --- | --- |
| `auth` | Sign up, sign in, password reset |
| `assistant` | Message extraction and operational questions |
| `payments` | Checkout creation and capture |
| `writes` | Order create, product create, inventory adjustment |

```python
class AssistantView(APIView):
    throttle_scope = "assistant"
```

Leave `/health/` and the verified PayPal webhook unthrottled by the user scopes. Protect the webhook with signature verification and idempotency, not by dropping retries.

Return DRF's `429` response. Do not add a custom rate-limit middleware.

## Permissions and auth

Once authentication exists, the default permission is `IsAuthenticated`. Use `AllowAny` only on sign-in, sign-up, health, and the PayPal webhook.

- Session or token auth stays on the server. Never accept a workspace id from the client as proof of access.
- Object permissions check store membership.
- Payment and order status changes check that the transition is legal, not only that the user is logged in.

## Payments and webhooks

- PayPal credentials come from the environment. Never from the client and never logged.
- Create and capture checkout on the server.
- Verify webhook signatures with PayPal's verification before changing payment state.
- Store the event id and ignore duplicates. Processing the same event twice must leave the order unchanged.
- Label sandbox state in API fields so the client can show that these are not live charges.

## Assistant endpoints

The model proposes a draft. The server validates it.

- Extraction returns structured fields the seller can edit. It does not create the order.
- Tool calls that read orders, products, or customers run server-side against the caller's store.
- Reject actions the MVP does not support with a clear 400 and a stable error code.
- Do not log full customer messages alongside secrets or payment payloads.

## Errors, settings, and logs

- Use DRF status codes: 400 validation, 401 unauthenticated, 403 forbidden, 404 missing or hidden by ownership, 409 illegal state transition, 429 throttled.
- Read configuration with `django-environ`. Document every new variable in `.env.example`.
- Log the operation, workspace, and object id. Do not log passwords, API secrets, or raw card data.
- Background work that can retry (webhook processing, email later) goes to Celery. Request/response work stays in the view.

## Tests

Test the behavior a demo can break:

- Serializer rejects an empty order and an unknown product.
- Creating an order blocks a quantity above stock.
- A user cannot read another store's order.
- A verified payment event moves the order to paid once.
- A duplicate webhook does not apply the payment twice.
- Throttled scopes return 429 after the configured limit.

Use DRF's `APIClient`. Cover serializers and API behavior. Skip tests that only assert Django internals.
