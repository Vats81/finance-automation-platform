# Deploying for friend testing

This gets the app onto a real public URL: **Render** for the backend + Postgres,
**Vercel** for the frontend. Both are free-tier and deploy straight from a GitHub
repo. Account creation and dashboard clicks below are yours to do (nobody but
you can create accounts on these services) — everything else was prepared for
you already.

**Known limitations of this setup** (fine for a testing round, not a permanent home):
- No real outbound email is configured, so the real "verify your email" link
  a stranger would get from Sign Up is never actually delivered — it only gets
  logged to Render's console. That's why the test accounts below are
  pre-verified via a seed script instead of the real signup form.
- Render's free web service spins down after ~15 minutes idle — the first
  request after a quiet period can take 30-50 seconds to wake back up.
- Render's free Postgres is retired after 30 days. Fine for a short test
  round; ask if you want it moved somewhere longer-lived later.
- AI Assistant / Insights / Receipt scanner and WhatsApp delivery stay on
  their "not configured" fallback messages unless you later add a real
  `ANTHROPIC_API_KEY` / Twilio credentials directly in Render's own env var
  UI — those are never handled by anyone but you.

## 1. Push this repo to GitHub

Create an empty repo on GitHub (any visibility), then hand the URL back so it
can be pushed.

## 2. Backend + Postgres on Render

1. Create a free Render account.
2. **New → PostgreSQL** (free plan). Once it's up, open it and copy the
   **"External Database URL"** (looks like `postgres://user:pass@host/db`).
3. **New → Web Service**, connect the GitHub repo, root directory `backend`,
   environment **Docker** (it will find `backend/Dockerfile` automatically).
   Free plan.
4. Under **Settings → Start Command**, override it to:
   ```
   sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
   ```
5. Add these environment variables:

   | Key | Value |
   |---|---|
   | `APP_ENV` | `production` |
   | `AUTH_DEV_MODE` | `false` |
   | `JWT_SECRET_KEY` | `f7fbc779f6300013e245e86060058bd296f1b6219c5aa35a4a66e5ebc6053264` |
   | `DATABASE_URL` | the External Database URL from step 2, with `postgres://` replaced by `postgresql+asyncpg://` |
   | `DATABASE_URL_SYNC` | the same URL, with `postgres://` replaced by `postgresql+psycopg2://` |
   | `CORS_ALLOWED_ORIGINS` | leave as `http://localhost:3000` for now — comes back in step 4 below |
   | `FRONTEND_BASE_URL` | same, leave as-is for now |

6. Deploy. Once it's live, copy the service's public URL
   (`https://financeai-backend-xxxx.onrender.com`) — you'll need it next.

## 3. Frontend on Vercel

1. Create a free Vercel account.
2. Import the same GitHub repo, set the project's **root directory** to `frontend`.
3. Add environment variables:

   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | the Render backend URL from step 2.6 |
   | `NEXT_PUBLIC_AUTH_DEV_MODE` | `false` |

4. Deploy. Copy the resulting URL (`https://your-project.vercel.app`).

## 4. Wire the backend back to the frontend

Back in Render, edit the backend's env vars:
- `CORS_ALLOWED_ORIGINS` → the Vercel URL from step 3.4
- `FRONTEND_BASE_URL` → the same Vercel URL

Saving triggers an automatic redeploy.

## 5. Create the test accounts

In Render, open the backend service's **Shell** tab and run:

```
python scripts/seed_demo_users.py
```

This creates the accounts below, pre-verified. Safe to re-run — it skips
whatever already exists.

| Email | Password | Role |
|---|---|---|
| `admin@financeai.app` | `Admin@FinanceAI2026!` | Platform admin (`/admin`) |
| `friend1@financeai-test.app` | `Friend1@Test2026!` | Regular user |
| `friend2@financeai-test.app` | `Friend2@Test2026!` | Regular user |
| `friend3@financeai-test.app` | `Friend3@Test2026!` | Regular user |
| `friend4@financeai-test.app` | `Friend4@Test2026!` | Regular user |
| `friend5@financeai-test.app` | `Friend5@Test2026!` | Regular user |

Each friend account lands on the onboarding screen on first login and creates
their own business from there — that flow is worth testing too, so it isn't
skipped.

## 6. Hand off both URLs

Send back the Render backend URL and the Vercel frontend URL so the deployed
app can be checked end-to-end (login as admin, login as a friend account,
confirm no console/CORS errors) before handing the Vercel link to friends.
