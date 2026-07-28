# API Documentation

FastAPI generates the API documentation directly from the route/schema definitions in `backend/app/*/api/`, so it's always in sync with the running code — nothing here is hand-maintained separately.

## Interactive docs

With the stack running (`docker compose up`):

- **Swagger UI**: http://localhost:8000/docs — try requests directly in the browser.
- **ReDoc**: http://localhost:8000/redoc — read-only, better for a full-schema overview.
- **Raw OpenAPI JSON**: http://localhost:8000/openapi.json — import into Postman/Insomnia, or feed to `openapi-typescript` to generate frontend types (a Phase 2 improvement — see [PHASE2_ROADMAP.md](../../PHASE2_ROADMAP.md)).

## Authenticating requests

Every endpoint except `/health` requires a bearer token:

```
Authorization: Bearer <token>
```

**In dev mode** (`AUTH_DEV_MODE=true`, the default), the token is `dev.<base64url-json>` where the JSON payload is `{"oid": "...", "email": "...", "name": "..."}` — see `backend/app/identity/infrastructure/entra/jwt_validator.py`. In Swagger UI, click **Authorize** and paste a token built this way, or copy one out of the frontend's `localStorage` (`fap.devAuth.session`) after logging in.

**Against real Entra ID**, acquire a token via MSAL (as the frontend does) for the `access_as_user` scope on the backend's App Registration, then use it the same way.

## Response shape

- Success responses return the resource JSON directly (see each context's `api/schemas.py`).
- Errors follow [RFC 7807](https://www.rfc-editor.org/rfc/rfc7807) `application/problem+json`:

  ```json
  {
    "type": "https://errors.finance-automation-platform.dev/vendor_missing_w9",
    "title": "VendorMissingW9Exception",
    "status": 422,
    "detail": "Vendor <id> cannot be activated without a W-9 on file",
    "instance": "/api/v1/vendors/<id>/activate",
    "error_code": "vendor_missing_w9"
  }
  ```

  `error_code` is the stable, machine-readable field to branch on — `title`/`detail` are for humans and may change.

## Rate limiting

Write endpoints (`POST`/`PATCH`) are rate-limited per client IP (`RATE_LIMIT_WRITE` in `.env`, default `30/minute`); reads fall back to `RATE_LIMIT_DEFAULT` (`100/minute`). Exceeding the limit returns `429` via [slowapi](https://github.com/laurentS/slowapi).

## Route map

| Prefix | Context | Notes |
|---|---|---|
| `/api/v1/me`, `/api/v1/users` | identity | current user, role assignment (Finance Admin only) |
| `/api/v1/vendors` | vendors | CRUD, W-9 upload, activation |
| `/api/v1/purchase-orders` | purchase_orders | create/list/get |
| `/api/v1/invoices` | invoices | submit, list/get, document attach |
| `/api/v1/approvals` | approvals | pending queue, approve/reject a step |
| `/api/v1/payments` | payments | list/get, manual status override (Finance Admin) |
| `/api/v1/audit-log` | audit | append-only event trail (Finance Admin only) |
