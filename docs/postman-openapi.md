# OpenAPI → Postman (Products / Stores)

Orbiz serves the live schema from the API. Export that into Postman for the hackathon demo.

## Schema URLs

| Env | Schema | Swagger UI |
| --- | --- | --- |
| Local Docker (`DEBUG=True`) | `http://localhost:8001/api/schema/` | `http://localhost:8001/api/docs/` |
| Non-debug | Same paths; **requires Bearer JWT** | Same |

## Import into Postman

1. Postman → **Import** → **Link** (or download the YAML/JSON from `/api/schema/`).
2. Paste `http://localhost:8000/api/schema/`.
3. After import, set collection auth to **Bearer Token** and paste an access token from `POST /api/v1/auth/login/`.
4. Base URL variable: `http://localhost:8001`.

## Key product requests to keep in the demo collection

- `GET /api/v1/stores/me/`
- `GET /api/v1/products/` (try `?low_stock=true`, `?out_of_stock=true`, `?is_active=true`)
- `POST /api/v1/products/`
- `POST /api/v1/products/{id}/adjust-stock/`
- `POST /api/v1/products/{id}/check-stock/` — **pre-check only**; Orders must reserve/deduct under lock
- `POST /api/v1/products/channel3/search/`
- `POST /api/v1/products/import-from-channel3/`

Re-export from `/api/schema/` after endpoint changes so Postman stays current.
