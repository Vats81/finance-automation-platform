# Phase 2+ Roadmap

The foundation slice ([README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md)) is a genuinely runnable, end-to-end Invoice/AP Automation system — but it's the first vertical slice of a much larger mandate, not the finished platform. This is the explicit list of what's deliberately deferred, and why deferring it was the right call for a foundation slice rather than an oversight.

## Infrastructure & delivery

- **CI/CD (GitHub Actions)**: lint, typecheck (`ruff`, `mypy`), test (`pytest`, `npm run build`), build/push Docker images, run `alembic upgrade head` as a migration-safety check on every PR.
- **Kubernetes manifests / Helm chart**: replace `docker-compose.yml` for any non-local environment — Deployments for `backend`/`celery-worker`/`celery-beat`/`frontend`, a Service + Ingress, ConfigMaps/Secrets for the `.env` values, HPA for the API and worker pools.
- **Terraform**: provision the real Azure resources this local stack currently emulates — Azure Database for PostgreSQL, Azure Cache for Redis, Azure Service Bus or a managed RabbitMQ, real Azure Blob Storage, Azure Key Vault for secrets, AKS cluster, Entra ID App Registrations.
- **Monitoring**: Prometheus scraping FastAPI's metrics endpoint (add `prometheus-fastapi-instrumentator`) and Celery's; Grafana dashboards for request latency/error rate, queue depth, outbox lag (`SELECT count(*) FROM outbox_messages WHERE published_at IS NULL`), and approval cycle time. Swap the OpenTelemetry console exporter (`shared/infrastructure/tracing.py`) for an OTLP exporter feeding a collector.
- **Secrets management**: Azure Key Vault (or equivalent) instead of `.env` files once past local dev.

## Auth & RBAC

- Sync roles from Entra ID App Roles / groups instead of the local `User.role` column, so role management lives in Entra ID rather than a bespoke admin endpoint.
- Fine-grained permission matrix beyond the current three roles (`AP_CLERK`, `APPROVER`, `FINANCE_ADMIN`) — e.g. per-vendor or per-department scoping.
- Multi-tenancy, if this is ever sold to more than one customer org.

## Domain depth

- **Real 3-way match**: `invoices/domain/matching/three_way_match.py` is a documented placeholder — needs a `Receiving`/`GoodsReceipt` bounded context to reconcile received quantity against both invoiced and ordered quantity.
- **Admin-configurable approval thresholds**: currently static via `.env` (`approvals/infrastructure/threshold_config.py`); make it a per-org, editable setting instead.
- **Real payment execution**: `Payment` in this slice is status-tracking only. Actual bank rails (ACH/wire, e.g. via a provider like Modern Treasury or Stripe Treasury), remittance details, reconciliation against bank statements.
- **OCR/document intelligence**: `invoices/infrastructure/document_processing_client.py` is explicitly simulated — line items are entered by the AP clerk at submission rather than extracted by ML. Swap in Azure AI Document Intelligence (or similar) behind the same `SimulatedDocumentProcessingClient` interface.
- **Additional bounded contexts**: Expense & Travel Management, Corporate Card / Spend Management — the other two product wedges considered at the start of this build (see the original scoping conversation), each as its own bounded context following the same Clean Architecture / DDD pattern established here.

## Frontend

- Generate TypeScript API types from `/openapi.json` (`openapi-typescript`) instead of hand-maintained `types/*.ts`, so frontend/backend contracts can't silently drift.
- Production Next.js build/hosting (currently `next dev` in the Docker Compose `frontend` service — fine for local dev, not for a real deployment).
- Real-time updates (WebSocket or SSE) instead of the invoice detail page's 2-second poll while a match is in flight.

## Testing

- `tests/integration/test_celery_ocr_task.py`: exercise the actual Celery task through a real broker (RabbitMQ via testcontainers) rather than invoking the underlying use case directly, once the value of that additional coverage outweighs the added test infrastructure.
- Load/performance testing for the outbox relay and matching logic at realistic invoice volumes.
- Contract tests between frontend and backend once the OpenAPI-generated types (above) exist.

## Platform hardening

- Idempotency keys on write endpoints (beyond the outbox's own at-least-once handling) to make client retries safe.
- Structured audit log retention/export policy (currently unbounded growth in `audit_log_entries`).
- `list_pending_for_role` (`approvals/infrastructure/repository_impl.py`) currently loads all in-progress workflows into Python to find the current step per workflow — fine at foundation-slice scale, worth a materialized "current step role" column if this becomes a hot path.
