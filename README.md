# Orbiz

Commerce ops workspace for the PayPal AI Hackathon: auth, store workspace, products/inventory, then orders and PayPal Sandbox.

## Stack

- **Backend:** Django + DRF, Postgres, Redis, Celery (`backend/`)
- **Frontend:** Vite + React + TypeScript (`frontend/`)

## Local setup

See `backend/.env.example` and `frontend/.env.example`. API defaults to host port **8001** via Docker Compose.

```bash
cd backend && docker compose up --build -d
cd ../frontend && npm install && npm run dev
```

## Tenancy, roles and billing

Three tiers:

- **Super admin** (platform): sees every store and user, invites store admins, and can suspend, deactivate or delete stores and users. Create the first one with `make superuser` (run from `backend/`; the Django `is_superuser` flag marks the super admin).
- **Store admin**: signs up directly (`/sign-up`) or accepts a super-admin invite, sets up the store, pays the mock **$5/month** plan, then manages the team and **roles** (`/team`, `/team/roles`).
- **Staff**: invited by email, with a role made of per-area permissions (view/create/edit/delete for products, orders, customers, team). The UI hides what they can't do and the API enforces it.

Suspending a store, or deactivating its admin, locks out everyone in it immediately. An unpaid or lapsed store is locked until the admin pays (`/billing`). Payments are a sandbox: no card is charged, and `DEBUG=True` also shows a decline simulator. A daily Celery beat task (`expire_subscriptions_task`) locks stores whose paid period ended.

In development, invite emails print to the backend console and the invite link is also shown in the UI.

Demo catalog + orders (after you have a seller account):

```bash
cd backend
docker compose exec backend python manage.py seed_demo_products --email your@email.com
docker compose exec backend python manage.py seed_demo_orders --email your@email.com
```

Sample Channel3 search in the UI: `black hoodie`.

## Channel3 (sponsor) — enrichment only

- Orbiz calls Channel3 **server-side** (`CHANNEL3_API_KEY` in `backend/.env` only — never `VITE_*`).
- Used for **search + import** into the seller’s Orbiz catalog (title, image, suggested price).
- Channel3 is **not** inventory truth and **not** checkout. Buy links are not used for payment.

## AG Grid (sponsor) — products + orders tables

- Products (`/products`) and Orders (`/orders`) use **AG Grid Community** via shared `frontend/src/components/data-grid.tsx`.
- Server filters, page-number pagination, and sort stay in the URL via `nuqs`; the grid renders the current page.

## Orders (§2.4)

- Draft → **Confirm** deducts stock under lock (`adjust_stock` reason `sale:{number}`); cancel restores with `cancel-restore:{number}`.
- **Fulfilment** and **payment** statuses are separate badges. Confirm sets fulfilment `unfulfilled` and payment `pending`.
- Processing / shipped / completed require `payment_status=paid` unless `allow_unpaid` is set explicitly (e.g. COD).
- `POST .../abandon-payment/` cancels a pending payment attempt without cancelling the order; `POST .../mark-paid/` remains an offline demo fallback.
- Cancel restores stock at most once (order row locked; second cancel → 409).

## Customers (§2.6)

- `/customers` lists every customer with **order count** and **last order date**, computed in one annotated query (`Count`/`Max` over `orders`) — no N+1 as the list grows.
- Filter by name/email/phone or an order-count range (`orders_min`/`orders_max`); sort by name, order count, or last order (customers with no orders always sort last).
- Customer profile shows contact details, internal notes, and the 5 most recent orders, with a link into the Orders grid pre-filtered to that customer (`/orders?customer_id=`).
- The order form's "Add customer" opens a dialog with the full form (name, email, phone, notes) instead of a name-only field, so a seller can capture an email on the spot for PayPal invoices and confirmations.
- No delete: `Order.customer` is `PROTECT`, so a customer with orders can't be removed from under them.

## Product images (S3-ready)

- Store a single **`image_url`** string on `Product` (HTTPS URL, max 2048). UI always renders `src={image_url}`.
- Today: Channel3 CDN URLs or a pasted link. **No local file upload / no S3 yet.**
- Later: upload to S3 → save the returned public (or CloudFront) URL into the same `image_url` field. Display code stays the same.

## Stock check vs reserve

- `POST /api/v1/products/{id}/check-stock/` is a **read-only pre-check** (used in the order form for warnings).
- Confirm (`POST /api/v1/orders/{id}/confirm/`) locks products, re-checks, and deducts in one transaction.

## API docs / Postman

See `docs/postman-openapi.md` — import from `http://localhost:8000/api/schema/`.

## PayPal Sandbox (§2.7)

- Credentials are **server-side only** (`PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_MODE`, `PAYPAL_WEBHOOK_ID` in `backend/.env` — never `VITE_*`).
- Order detail → **Create PayPal checkout** → approve in Sandbox → the approval webhook captures on the server (or return/`capture`) → `payment_status=paid`.
- **Send PayPal invoice**: PayPal emails the buyer an invoice (blank email = shareable link only); the `INVOICING.INVOICE.PAID` webhook marks the order paid. Only one payment request is open per order.
- **Refund via PayPal**: full or partial, from order detail → `partially_refunded` / `refunded`. Refunds made in the PayPal dashboard sync back by webhook.
- Webhook: `POST /api/v1/payments/webhooks/paypal/` (signature verified; duplicate event ids are ignored). Needs a public HTTPS URL (e.g. a dev tunnel with **public** visibility) and `PAYPAL_WEBHOOK_ID`. Subscribe to: `CHECKOUT.ORDER.APPROVED`, `CHECKOUT.ORDER.COMPLETED`, `CHECKOUT.ORDER.DECLINED`, `PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.CAPTURE.DENIED`, `PAYMENT.CAPTURE.REFUNDED`, `PAYMENT.CAPTURE.REVERSED`, `PAYMENT.REFUND.PENDING`, `PAYMENT.REFUND.FAILED`, `INVOICING.INVOICE.PAID`, `.CANCELLED`, `.REFUNDED`, `.SENT`, `.UPDATED`.
- Prefer a **USD** demo store; amount/currency come from the Orbiz order. Currencies PayPal can't take (e.g. PKR) are blocked with a clear message; `PAYPAL_SUPPORTED_CURRENCIES` controls the allow-list.
- The Sandbox app needs **Invoicing** enabled. PayPal never sends real email from Sandbox, and its Developer Dashboard → Sandbox → Notifications page was not showing any new emails (checkout receipts, refunds or invoices) when we tested — so demo the invoice through **Open invoice** / **Copy invoice link** (use a Sandbox buyer email, `sb-…@personal.example.com`, as the recipient).
- Offline fallback: **Mark paid (demo)** when Sandbox credentials or tunnel are unavailable (such orders have no PayPal payment to refund).
- Channel3 does not replace PayPal.

### Demo sequence

1. Confirm order (stock deducted, payment `pending`).
2. Create PayPal Sandbox checkout; open the approve link — or send a PayPal invoice instead.
3. Pay with a Sandbox buyer; Orbiz marks the order paid from PayPal's webhook (the tab can stay closed).
4. Order shows Paid; advance fulfilment.
5. Refund part or all of the payment from the order; the badge follows (Partially refunded / Refunded).

## Docs

- Products: `docs/2.5-products-and-inventory-feature-spec.md`, `docs/2.5-map.md`
- PayPal: `docs/2.7-paypal-payments-feature-spec.md`, `docs/2.7-map.md`
- Orders planning (outside repo): `E:/FlowMatx/2.4-orders-and-order-details-feature-spec.md`, `E:/FlowMatx/2.4-map.md`
