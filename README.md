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
- `POST .../abandon-payment/` cancels a pending payment attempt without cancelling the order; `POST .../mark-paid/` is demo-only until §2.7 webhooks.
- Cancel restores stock at most once (order row locked; second cancel → 409).
- PayPal Sandbox checkout is stubbed on order detail until §2.7.
- Thin customers API supports order create (`/api/v1/customers/`).

## Product images (S3-ready)

- Store a single **`image_url`** string on `Product` (HTTPS URL, max 2048). UI always renders `src={image_url}`.
- Today: Channel3 CDN URLs or a pasted link. **No local file upload / no S3 yet.**
- Later: upload to S3 → save the returned public (or CloudFront) URL into the same `image_url` field. Display code stays the same.

## Stock check vs reserve

- `POST /api/v1/products/{id}/check-stock/` is a **read-only pre-check** (used in the order form for warnings).
- Confirm (`POST /api/v1/orders/{id}/confirm/`) locks products, re-checks, and deducts in one transaction.

## API docs / Postman

See `docs/postman-openapi.md` — import from `http://localhost:8000/api/schema/`.

## PayPal — payment path

- Checkout and money stay on **Orbiz → PayPal Sandbox** (§2.7), after Orders (§2.4).
- Channel3 does not replace PayPal.

## Docs

- Spec + tracker: `docs/2.5-products-and-inventory-feature-spec.md`
- File map: `docs/2.5-map.md`
- Orders planning (outside repo): `E:/FlowMatx/2.4-orders-and-order-details-feature-spec.md`, `E:/FlowMatx/2.4-map.md`
