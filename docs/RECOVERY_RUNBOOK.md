# Backup and recovery runbook

Audience: the **recovery operator** (the platform owner). Business Admins never
receive platform backups and have no restore access. No secret appears in this
file - only the names of the places they are stored.

## 1. Targets (proposed - NOT yet measured)

| Requirement | Target | Status |
|---|---|---|
| Recovery point objective (max data loss) | 24 hours | Designed for (daily backup). **Measured value: none yet.** |
| Recovery time objective | 4 hours | **Measured value: none yet** - fill in section 7 after the first drill. |
| Backup schedule / retention | Daily, 30-day rolling | Implemented in `.github/workflows/backup.yml` (artifact `retention-days: 30`). |
| Restore drill | Before beta, monthly, after major schema changes | Workflow `restore-drill.yml` written; **first run pending** (needs the isolated database, see 5). |

Do not promise these to users until section 7 shows measured results that meet
them.

## 2. What is backed up

* **Every table in the schema** (not a hand-kept list): users and password
  hashes, businesses, memberships and roles, customers, vendors, products
  (current stock quantity), sales (line items and amounts received are columns of
  the sale row), purchases, expenses, contact requests, business audit events,
  and the legacy AP tables.
* **Migration/schema version** (`alembic_version`), recorded in the manifest.
* A **manifest** with a row count and sha256 per table, the generation time and
  the app commit.

Deliberately **not** in the backup:

* `outbox_messages` - a delivery queue; restoring it would replay old
  emails/WhatsApp messages.
* One-time email-verification and password-reset token hashes (they expire).

Known gaps (do not hide these from users):

* **Uploaded documents.** No document storage is deployed (`AZURE_STORAGE_*`
  unset), so there are none to back up. If it is ever enabled, that container
  needs its own backup and the drill must verify the files exist.
* **Stock movement history.** The schema stores only each product's current
  quantity, not a movement ledger, so history cannot be restored because it does
  not exist. (Quantities are restored exactly.)
* Backups contain **password hashes** (bcrypt). Without them every user would
  need a password reset, which needs working email. They are acceptable only
  because the file is encrypted before leaving the runner and the endpoint is
  platform-admin only.

## 3. Where backups live and who can read them

* Created by `GET /admin/backup` (platform admin only), called daily by the
  `Scheduled backup` GitHub workflow at 03:17 UTC.
* Integrity-checked on the runner (`backend/scripts/verify_backup.py`: manifest,
  checksums, schema version, non-empty users/businesses, generated within the
  last hour). A bad backup fails the job.
* Encrypted with AES-256 (gpg symmetric) **before** upload, stored as a GitHub
  Actions artifact. This is a different failure domain from the Neon database.
* Secrets (names only): `BACKUP_ADMIN_EMAIL`, `BACKUP_ADMIN_PASSWORD`,
  `BACKUP_ENCRYPTION_PASSPHRASE` in GitHub repository secrets. **Keep a copy of
  the passphrase in your password manager - without it backups are unreadable.**
* Note: the repository is public, so artifacts are only as private as the
  encryption. Use a strong passphrase. Consider making the repository private.

## 4. Monitoring and alerts

* `Scheduled backup` fails (GitHub emails the repo owner) if the endpoint
  errors, authentication fails, or the backup is empty/corrupt/too small.
* `Backup monitor` runs daily and fails - and opens or updates a GitHub issue
  titled "Backup problem" - when there is **no successful backup in the last 36
  hours**, the artifact is missing/expired, or it is implausibly small. This
  catches the case a failure alert cannot: the schedule silently stopped.
* GitHub pauses scheduled workflows on repos with no activity for 60 days. The
  monitor and the monthly drill both need the repo to stay active; if you stop
  committing, run a workflow manually each month.

## 5. One-time setup for the restore drill

1. Create a **separate, empty Postgres database whose name contains `drill`**
   (for example a new Neon project `finance-restore-drill`). It must never be the
   production database.
2. Add its connection string as repository secret `DRILL_DATABASE_URL`.
3. The workflow refuses to run unless the URL contains `drill`, and the script
   refuses if the target is the same database as `DATABASE_URL`.

## 6. Procedure: restore (real incident)

1. **Select the recovery point.** Actions -> Scheduled backup -> pick the newest
   run that is green. Expected data loss = time since that run.
2. **Download and decrypt.**
   `gpg --batch --yes --passphrase "<from password manager>" --decrypt backup-XXXX.json.gpg > backup.json`
3. **Verify integrity.** `python backend/scripts/verify_backup.py backup.json`
   must print `BACKUP OK`. If it does not, use the previous day's backup.
4. **Provision a new empty Postgres** (new Neon project) - do not restore over
   the damaged database until the restored copy is validated.
5. **Restore and reconcile** (runs migrations to the backup's schema version,
   loads all rows in one transaction, compares every table and business):
   ```
   export RESTORE_DATABASE_URL="<new empty database url>"
   cd backend
   python scripts/restore_backup.py ../backup.json --confirm-isolated --migrate --report ../restore-report.json
   ```
   Exit code 0 means every table checksum, every per-business total, all
   memberships/roles and referential integrity matched.
6. **Apply compatible migrations.** If the app has newer migrations than the
   backup, run `alembic upgrade head` against the new database.
7. **Validate with the app, side effects off.** Start the API against the new
   database with `DISABLE_EXTERNAL_SIDE_EFFECTS=true` (email/WhatsApp become
   log-only, Stripe keys blanked). Log in as a known user; open a business;
   check dashboard totals against `restore-report.json`.
8. **Approve cutover.** Only after step 7: point Render's `DATABASE_URL` at the
   new database and redeploy; unset `DISABLE_EXTERNAL_SIDE_EFFECTS`. Run `/health`
   and a smoke test.
9. **Keep a rollback.** Leave the old database untouched for at least 7 days.
   Rolling back = point `DATABASE_URL` back (data written since cutover would be
   lost, so decide quickly).

## 7. Drill record (fill in after every drill)

Run the `Restore drill` workflow; copy its job summary here. A drill counts only
if the reconciliation **PASSED**.

| Date | Backup taken | Backup age at drill | Rows | Restore time | Total drill time | Result | Notes |
|---|---|---|---|---|---|---|---|
| _none yet_ | | | | | | | |

Measured RPO = the age of the newest backup at the worst moment (just before the
next one runs) = up to 24h + the time to detect a failure. Measured RTO = total
drill time plus the time to provision a database and cut over. Mark the feature
ready **only** when both are measured and meet the targets in section 1.

## 8. Supplementary protection (not relied on)

Neon keeps a short history for point-in-time restore on its own plans; check the
current window in the Neon console and treat it as a convenience for "I just
deleted something" mistakes, not as the disaster-recovery plan (it shares the
provider's failure domain).
