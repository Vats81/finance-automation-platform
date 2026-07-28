# Finance Automation Platform

An Invoice / Accounts Payable automation platform — the foundation slice of a larger Finance Automation Platform (competing with the AP-automation space occupied by Tipalti, SAP Concur, Ramp, and UiPath-style workflow automation).

Vendor onboarding → invoice submission → 2-way match against a purchase order → threshold-based multi-step approval → reactive payment scheduling → append-only audit trail, all built with Clean Architecture, Domain-Driven Design, and SOLID principles on a real async, event-driven backend.

See [ARCHITECTURE.md](ARCHITECTURE.md) for how it's put together and [PHASE2_ROADMAP.md](PHASE2_ROADMAP.md) for what's deliberately not in this slice yet.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Frontend | Next.js 15 (App Router), React 18, TypeScript, Tailwind CSS |
| Database | PostgreSQL 16 |
| Cache / broker backend | Redis 7 |
| Message broker | RabbitMQ 3.13 |
| Background workers | Celery (worker + beat) |
| File storage | Azure Blob Storage (Azurite emulator for local dev) |
| Auth | Microsoft Entra ID (OIDC, resource-server pattern) + local dev-mode bypass |
| Containerization | Docker, Docker Compose |

## Prerequisites

- Docker Desktop (or a Docker-compatible engine) with Docker Compose
- That's it for local dev — the rest runs inside containers.

## Quick start

```bash
git clone <this-repo>
cd finance-automation-platform

cp .env.example .env
cp frontend/.env.local.example frontend/.env.local

docker compose up --build
```

This brings up Postgres, Redis, RabbitMQ, Azurite, the FastAPI backend (auto-runs `alembic upgrade head` on start), a Celery worker, Celery beat, and the Next.js frontend.

- Frontend: http://localhost:3000
- API docs (Swagger UI): http://localhost:8000/docs
- RabbitMQ management UI: http://localhost:15672 (user/pass from `.env`)

### First login

`AUTH_DEV_MODE=true` by default (both backend `.env` and frontend `.env.local`) — the platform runs end-to-end **without a real Entra ID tenant**. The login page accepts any email/name and JIT-provisions a user in the `AP_CLERK` role.

To get a Finance Admin (needed to activate vendors and approve larger invoices) and a sample Approver without the chicken-and-egg problem of role assignment itself requiring a Finance Admin, seed them:

```bash
docker compose exec backend python scripts/seed_dev_data.py
```

Then log in via the dev-mode form using `admin@example.com` (Finance Admin), `approver@example.com` (Approver), or `clerk@example.com` (AP Clerk) — the seeded Entra object ids match exactly what the dev-mode login generates for those emails.

### Golden path

1. Sign in as `clerk@example.com`.
2. **Vendors** → New vendor → fill in details → create.
3. Open the vendor → upload any file as the W-9 → **Activate vendor**.
4. **Purchase Orders** → create a PO against that vendor with a line item.
5. **Invoices** → Submit invoice → pick the PO (line items pre-fill from it) → submit. The status starts at `submitted` and moves to `matched` within a couple of seconds once the Celery worker processes it.
6. If the line items were edited to differ from the PO, the invoice lands in `match_exception` with the discrepancies listed instead.
7. On a match, an approval workflow starts automatically (1–3 steps depending on the invoice total vs. `APPROVAL_THRESHOLD_L1_MAX`/`L2_MAX` in `.env`).
8. Sign in as `approver@example.com` (or `admin@example.com` for larger amounts) → **Approvals** → approve.
9. Once every step is approved, the invoice becomes `approved` and a `Payment` is scheduled automatically (NET-30) — visible under **Payments**.
10. **Audit trail** (Finance Admin only) shows every domain event raised along the way.

### Real Entra ID instead of dev mode

Register two App Registrations in Entra ID (one SPA, one API exposing an `access_as_user` scope), then set `AUTH_DEV_MODE=false` plus the `ENTRA_*` / `NEXT_PUBLIC_ENTRA_*` variables in both env files.

## Running tests

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate  # or source .venv/bin/activate
pip install -e ".[dev]"

pytest tests/unit                 # pure domain/application logic, no external deps
pytest tests/integration -m integration   # real Postgres via testcontainers — needs Docker
```

Frontend:

```bash
cd frontend
npm install
npm run typecheck
npm run build
```

## Project layout

```
finance-automation-platform/
├── docker-compose.yml
├── backend/            # FastAPI app — see ARCHITECTURE.md for the layering
├── frontend/            # Next.js app
└── docs/api/            # API documentation notes
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — Clean Architecture layering, DDD bounded contexts, the transactional outbox pattern, system diagram.
- [PHASE2_ROADMAP.md](PHASE2_ROADMAP.md) — what's deliberately deferred (K8s, Terraform, CI/CD, monitoring, Fabric, additional bounded contexts, real payment rails).
- [docs/api/README.md](docs/api/README.md) — where to find the API docs and how to authenticate against them.
