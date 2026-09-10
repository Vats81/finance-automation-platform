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
3. **New → Web Service**, connect the GitHub repo. On the creation form,
   explicitly set **Language** to **Docker** (don't let it auto-detect —
   it can guess wrong on a monorepo). **Root Directory**: `backend`.
   **Dockerfile Path**: leave blank/default — resolves to `backend/Dockerfile`
   once Root Directory is set. **Instance Type**: Free.
4. Leave the **Docker Command** field **blank**. Migrations-then-start is
   already baked into `backend/Dockerfile`'s own `CMD`
   (`alembic upgrade head && uvicorn ...`) — Render's Docker Command
   override field doesn't reliably pass shell operators like `&&` through
   no matter how it's quoted, so don't fight it; the Dockerfile's default
   command already does the right thing. Set **Health Check Path** to
   `/health` — though note `/health` also checks Redis (never deployed
   here), so it always reports unhealthy/503 regardless of whether the app
   is actually fine; you can leave the Health Check Path blank instead if
   Render's own health-gating on that gives you trouble.
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

Render's **free** plan doesn't include Shell access, so
`scripts/seed_demo_users.py` can't be run interactively there. Instead:

1. In Render, add a temporary env var `SEED_SECRET` set to any random
   string you pick (this disables/enables a one-time seeding endpoint —
   blank by default, so it's safe to leave the code in place).
2. Save (triggers a redeploy).
3. Visit this URL in your browser once (replace the secret with what you
   set):
   ```
   https://<your-backend-url>/internal/seed-demo-users?secret=<your-secret>
   ```
   It returns JSON listing which accounts were created.
4. Optional but recommended: blank out `SEED_SECRET` again afterward to
   lock the endpoint back down.

(If you're on a paid Render plan with Shell access, `python scripts/seed_demo_users.py`
run from the Shell tab does the same thing and never needs the endpoint at all.)

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

## 7. Optional: turn on real integrations

Everything below is off by default (Console/no-op fallbacks) and turning
each one on is just adding env vars in Render — no code changes. Check
`/app/integrations` in the app to see live connected/not-configured status
for each.

**Outbound email** (real signup verification / password reset / report
delivery). **Use the Resend API, not SMTP** — Render (and several other
free-tier hosts) silently block outbound SMTP ports, so an SMTP host/port/
credentials setup will time out no matter how correct it is. [Resend](https://resend.com)'s
HTTPS API sidesteps that entirely:

| Key | Value |
|---|---|
| `RESEND_API_KEY` | your Resend API key (`re_...`) |
| `SMTP_FROM_ADDRESS` | an address on your verified sending domain (still used as the "From" address for Resend-sent mail) |

(If you're deploying somewhere that doesn't block outbound SMTP, the
`SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/`SMTP_PASSWORD` vars still work as
a fallback — `RESEND_API_KEY` takes priority over them when both are set.)

_No sending domain yet?_ Resend's shared/sandbox key only delivers to your
own verified address, so friends' signup-verification emails never arrive
and they can't log in. Until you verify a real domain, set
`AUTH_AUTO_VERIFY_EMAIL=true` — new signups are then created
already-verified and can log in straight away. Flip it back to `false`
(or drop it) once real email works.

**WhatsApp delivery** (via [Twilio](https://twilio.com) — start with their
free WhatsApp Sandbox):

| Key | Value |
|---|---|
| `WHATSAPP_PROVIDER` | `twilio` |
| `TWILIO_ACCOUNT_SID` | from the Twilio Console |
| `TWILIO_AUTH_TOKEN` | from the Twilio Console |
| `TWILIO_WHATSAPP_FROM` | your Twilio WhatsApp number, e.g. `+14155238886` |

**AI Assistant / Insights / Forecasting / Receipt Scanner** — pick one provider.

_Free, no credit card_ (via [Groq](https://console.groq.com)):

| Key | Value |
|---|---|
| `AI_PROVIDER` | `groq` |
| `GROQ_API_KEY` | your API key from console.groq.com |
| `GROQ_MODEL` | `openai/gpt-oss-120b` (default) — Assistant / Insights / Forecasting |
| `GROQ_VISION_MODEL` | `qwen/qwen3.8-27b` (default) — Receipt Scanner |

Groq changes its hosted model list fairly often — if a call 404s with a
`model_not_found` error, list the current ids with
`curl -s https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"`
and update the two vars above (`GROQ_MODEL` needs `tools` in its
`supported_features`; `GROQ_VISION_MODEL` needs `image` in
`input_modalities`).

_Paid_ (via [Anthropic](https://console.anthropic.com)):

| Key | Value |
|---|---|
| `AI_PROVIDER` | `anthropic` |
| `ANTHROPIC_API_KEY` | your API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-5` (already the default) |

**Subscription billing** (via [Stripe](https://dashboard.stripe.com/register) —
stay in **Test mode** first, no real money involved):

1. **Products** → create "Starter" and "Pro" recurring prices, copy each
   **Price ID** (`price_...`).
2. **Developers → API keys** → copy the **Secret key** (`sk_test_...`).
3. **Developers → Webhooks** → add an endpoint at
   `https://<your-backend-url>/api/v1/billing/webhook`, subscribed to
   `checkout.session.completed`, `customer.subscription.updated`, and
   `customer.subscription.deleted` → copy its **Signing secret** (`whsec_...`).

| Key | Value |
|---|---|
| `STRIPE_SECRET_KEY` | your `sk_test_...` (or `sk_live_...` once ready for real charges) key |
| `STRIPE_WEBHOOK_SECRET` | your `whsec_...` signing secret |
| `STRIPE_PRICE_ID_STARTER` | the Starter price id |
| `STRIPE_PRICE_ID_PRO` | the Pro price id |

Once set, a business owner sees real "Upgrade to Starter/Pro" buttons on
`/app/settings` instead of the free unpaid plan selector, and plan changes
sync automatically via the webhook. Test with Stripe's published test card
`4242 4242 4242 4242` (any future expiry/CVC) before ever using a real card.

**Error tracking** (via [Sentry](https://sentry.io) — free tier available):

| Key | Value |
|---|---|
| `SENTRY_DSN` | your project's DSN from Sentry's onboarding flow |

Leave blank to disable entirely (the default) — no code changes needed
either way.

## 8. Backups

There's no automated backup schedule (that would need a always-on
scheduler, which this deployment deliberately doesn't run — see the
Celery/Redis notes elsewhere in this repo). Instead, a platform admin can
trigger a manual backup any time:

```
GET /api/v1/admin/backup
```

(with a platform-admin's bearer token in the `Authorization` header) —
downloads a JSON file with every row of every SMB table. It's a logical
backup (JSON, not a SQL dump), restorable by reading the file back in
rather than piping it into `psql` directly. Good enough for occasional
manual snapshots; revisit with a real scheduled `pg_dump` if this becomes
a production system with real customer data.

## 9. Legal pages

`/terms` and `/privacy` are live with starter template content (clearly
marked as a draft, not legal advice) — have an actual lawyer review and
adapt them before relying on this with real customers.
