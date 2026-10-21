# Private beta - readiness gates

Status as of 2026-10-21. **The beta is NOT ready.** The gates below must all be
green before anyone is invited. "Verified" means it was run and the evidence is
named; "Not run" means exactly that. Nothing here is a guess dressed as a pass.

## Onboarding release gate

| # | Gate | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Backend RBAC and tenant-isolation tests pass | **Verified** | `backend/tests/unit/api/test_route_permissions.py` (static audit of every business route + HTTP matrix of each role, non-members, cross-tenant ids, removal / role change / suspension on the next request, owner and self-escalation rules). Live run against production: 139 checks, 0 failed (`live_rbac_check.py`, throwaway [QA] accounts). **Not covered live:** suspending a business (needs a platform-admin login; covered by the unit tests only). |
| 2 | Measured restore drill | **Not run** | Tooling, CI workflow and runbook exist and are unit-tested on SQLite (`docs/RECOVERY_RUNBOOK.md`). The drill needs an isolated Postgres whose name contains `drill` and the `DRILL_DATABASE_URL` secret. Until it has run, RPO/RTO are **unmeasured**. |
| 3 | Reconciled exports | **Partly verified** | The P&L PDF was downloaded from production for the known fixture and its printed figures (3,250.00 / 1,585.50 / 1,664.50, period, currency) match the dashboard. Not verified: opening the PDF in a viewer by eye; the on-page CSV download (client-side) was verified by code and a helper test only; multi-month ranges and negative profit checked in unit tests, not live. |
| 4 | Financial-mutation tests | **Verified** | Negative/oversized money, discount > subtotal, zero expenses, overpayment, edits below money received, void rules, stock floor, duplicate invoice numbers, idempotent retries (unit tests + live probe `live_integrity_probe.py`). **Known gap:** stock is not changed by sales or purchases (no product link on line items), so there is no automatic stock reconciliation to test; stock changes only through manual adjustments. |
| 5 | AI contradictions resolved | **Verified for the fixture** | Live: total sales, expenses, profit, biggest expense, an explicit period, a "can you delete my sales?" injection attempt and an off-topic question all answered correctly / refused. Not verified: a large real dataset, customer-name injection beyond the unit test, other phrasings. Keep AI labelled as an assistant that can be wrong. |
| 6 | Remaining limitations recorded and support contact provided | **Open** | Limitations are listed below. **A support contact has not been chosen** - add one before inviting anyone. |

## Verified in this round

* Permissions: single matrix in `backend/app/business/api/permissions.py`; viewers can no longer export; suspended businesses lose access on the next request; the Owner role cannot be granted by invite or role change; members cannot change their own role; the owner cannot be removed; the legacy, unscoped AP endpoints are not mounted.
* A removed-then-re-invited member used to get a 500 on every request (duplicate membership rows). Fixed and covered by a live check.
* Audit trail (`business_audit_events`): actor, role, route, record id and status for every successful mutation; no payloads. Owner/Admin can read it.
* Idempotency: `Idempotency-Key` makes retries and double-clicks safe; five concurrent identical POSTs now create one record.
* CSV import: encoding, delimiters, mapping, limits (5 MB / 3,000 rows), row errors, re-upload idempotency, live progress for large files.

## Not verified (needs a real browser or a person)

* 375 px / 768 px layouts, keyboard-only flows, visible focus, Esc dismissal, the guided tour, PWA installation, offline behaviour.
* Opening exported files in Excel / a PDF viewer; CSV formula-injection with real spreadsheet software (the exporter escapes `= + - @` cells; this was tested in code, not in Excel).
* Email delivery to anyone other than the account owner (the email provider is in test mode).

## Known limitations to disclose to beta users

* Email and WhatsApp are in test/limited mode; invitations and report sends to other people may not arrive.
* Billing is not connected. Currency is USD only.
* Stock is manual (not reduced by sales); there is no movement history.
* Data lives on free-tier hosting that sleeps when idle (first request can take 30-60 s) and has no uptime guarantee.
* Backups: daily, 30-day retention, encrypted - but **restore has not been proven yet** (gate 2).
* Imports of ~3,000 rows take about a minute.
* The AI assistant is read-only and can still misword an answer; figures come from the system, but check anything important.

## Waitlist and invitations

* `/beta` (not linked anywhere) registers interest only; it creates no account. `/admin/beta-waitlist` tracks Interested -> Qualified -> Waiting for checks -> Invited -> Onboarded / Paused, and refuses to skip steps.
* Moving someone to "Invited" sends nothing. Outreach drafts are in `docs/BETA_OUTREACH_DRAFTS.md` and are **unsent drafts**.
* Start free, set each business up together, review feedback weekly, and keep the original spreadsheets and receipts for reconciliation.
