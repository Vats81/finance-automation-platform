# Private beta - operator playbook

For the owner. It covers: the go/no-go check, switching the beta on, running
each person through the pipeline, the first session, the weekly rhythm, and
what to do when something goes wrong. Nothing here is sent automatically; you
send every message yourself.

Companion files: `BETA_READINESS.md` (gate status), `BETA_OUTREACH_DRAFTS.md`
(unsent message drafts), `BETA_TESTER_GUIDE.md` (give this to testers),
`RECOVERY_RUNBOOK.md` (backups and restore).

## 1. Go / no-go before you invite anyone

Do not send an invitation until every box is ticked.

- [ ] **Restore drill has run and PASSED** (GitHub → Actions → "Restore drill").
      Write the result in `RECOVERY_RUNBOOK.md` section 7. *Not done yet.*
- [ ] **A support contact exists** and is monitored (a shared mailbox, not your
      personal inbox). Put it in the tester guide in place of `{{support_email}}`.
- [ ] **Invite-only sign-up is ON** (section 2) and you tested that an
      uninvited email is refused.
- [ ] **Email can actually reach testers.** Email is in Resend test mode, which
      only delivers to the account owner, so a tester's **password-reset email
      will not arrive**. Before inviting, verify a sending domain in Resend and
      set `SMTP_FROM_ADDRESS` to an address on it (Integrations page should
      then drop the "Limited" label). Without this, a forgotten password means
      you must delete and recreate the tester's account (Admin → Users).
- [ ] **Backups are green**: the last "Scheduled backup" run succeeded and the
      "Backup monitor" is green.
- [ ] **Uptime monitor** on `/ping` is running (5-minute checks, alert to your
      phone/email).
- [ ] **QA data removed**: no `[QA]` businesses, firms, users or waitlist rows.
      Run `python backend/scripts/purge_qa_data.py` (a preview), then again with
      `--apply`; it needs `FINVERLO_API`, `ADMIN_EMAIL` and `ADMIN_PASSWORD` in your
      environment. The demo account and `qa_demo_account.txt` are deleted.
- [ ] **Secrets cleaned**: `SEED_SECRET` and `SEED_ADMIN_PASSWORD` are not set in
      Render.
- [ ] **You have done the demo walkthrough yourself in a browser** on a laptop
      and a phone, with a real bill, and noted anything odd.
- [ ] **You know your answer** to "what happens to my data?" (section 8).

Start with **3 businesses, not 5** - one or two weeks later, add more.

## 2. Switching the private beta on

In Render → your backend service → Environment, add:

| Variable | Value | Why |
|---|---|---|
| `REGISTRATION_REQUIRES_INVITE` | `true` | Only emails you have moved to **Invited** on the waitlist can create an account |
| `CONTACT_INBOX_EMAIL` | your support address (optional) | Get an email for each demo-request form |

Save, let it redeploy, then **test it**: try to sign up with an address that is
not on the waitlist - you should see "Sign-up is by invitation during the
private beta." Then invite one test address of your own (section 3), sign up,
confirm it works, and delete that test account afterwards.

To open sign-up to everyone again, remove the variable (or set it to `false`).

How it works: sign-up is allowed only for a waitlist entry in status
**Invited** (or **Onboarded**). When an invited person creates their account,
their entry moves to **Onboarded** by itself. Team members a business owner adds
later must *also* be invited here first (add them to the waitlist yourself with
their email, qualify, invite), because they need an account too.

## 3. The pipeline for each person

The admin page is **Admin → Beta waitlist**. Statuses and what they mean:

| Status | Meaning | You do |
|---|---|---|
| Interested | They filled in the form (or you added them) | Read their answers |
| Qualified | They fit: spreadsheets today, a real reporting problem, willing to give weekly feedback | Book a 20-minute call |
| Waiting for checks | You want to hold them until a gate passes | - |
| Invited | You have decided to let them in; they can now sign up | Send the invitation (draft 4) |
| Onboarded | They created an account | Run the first session |
| Paused | Not now / left | Keep or delete their details |

Moving someone to "Invited" **sends nothing** - you send the email yourself.

**Collecting interest:** the form is at `/beta` and is not linked from the site.
Share the link yourself with people you choose. It never creates an account.

**Qualifying call (20 min):**
1. How do you keep your books today? What does a month-end look like?
2. What report do you most wish you had?
3. Roughly how many sales/expenses a month? (Under ~300 is ideal.)
4. Are you able to give 10 minutes of feedback every week?
5. Set expectations: free, early, supervised, USD only, keep your spreadsheets.
6. Ask them *not* to share bank details; agree to start with one month of data.

**Invitation:** use draft 4 in `BETA_OUTREACH_DRAFTS.md`, with the real known
limits, the tester guide attached, and your support address. Invite from the
same email address you put on the waitlist - sign-up only works for that exact
address.

## 3b. Setting up each business (first session, 45 minutes, screen-share)

1. They sign up and log in (remind them sign-up doesn't log in automatically).
2. They create the business (name; USD).
3. Together, import **one month** of their real data via **Data Upload**
   (customers, products, expenses - CSV exports from their spreadsheet). Fix
   column names in the mapping step; read the row errors aloud.
4. Add 3-5 sales by hand to see the flow, record a payment.
5. Scan one real supplier bill; add to stock if they track inventory.
6. Open the Dashboard and **reconcile one number against their spreadsheet**
   while you are both looking. Write down the result.
7. Ask 2-3 AI questions whose answers they can check.
8. Agree the weekly check-in time and give them the tester guide.

Record afterwards (a simple table is enough): date, business, what they
imported, reconciliation result, problems found, mood.

## 4. The weekly rhythm

* **Monday:** look at Admin → Beta waitlist, answer new interest, decide on
  invitations. Check the three health signals: last backup green, backup
  monitor green, uptime monitor green.
* **Mid-week:** a 10-minute message or call per active tester: "did the numbers
  match this week? what annoyed you?"
* **Friday:** triage the week's feedback into three buckets - wrong numbers
  (fix first), blockers (fix next), nice-to-have (log). Tell testers what you
  fixed.
* **Every week:** pick one tester and re-do one reconciliation yourself from
  their spreadsheet. A wrong number is the one thing that ends a beta.

### What to measure

* Reconciliation matches (target: every checked figure matches).
* Time to first useful report after sign-up.
* Number of problems reported per tester, and how many were wrong numbers.
* Would they be disappointed if it went away? (Ask at week 2 and week 4.)

## 5. When something goes wrong

| Situation | What to do |
|---|---|
| App won't load / "stuck" | Wait a minute (free hosting wakes slowly), then open `/health` on the backend. `"degraded"` for Redis is normal. If Postgres is not "ok", see `DEPLOY.md` section 12 |
| A tester says a number is wrong | **Treat as top priority.** Ask for the exact figure, the period and the source. Reproduce in their business (Admin can't read data - ask them to share a screen). Fix, then re-verify |
| A tester can't sign up | Is their exact email on the waitlist as **Invited**? Typos and aliases are the usual cause |
| A tester forgot their password | They use "Forgot password". **If email is still in test mode it will not arrive**: use Admin → Users → **Reset password**. It shows a new temporary password once; pass it to them privately and ask them to change it. Their old password stops working immediately, but a session they already hold lasts until it expires, so deactivate the account first if you suspect it was taken over. Fix email too (section 1) |
| Scans fail with "busy" | The free AI service rate limit; wait a minute. If it's constant, tell me |
| Someone entered the wrong data | They can edit or void records themselves; a purchase that added stock must be voided to change its items |
| A business must be removed | Admin → Businesses → Delete (type the name), then Users → Delete. Permanent |
| Data loss or corruption | Follow `RECOVERY_RUNBOOK.md` section 6. Tell affected testers promptly and honestly |
| A security concern | Rotate `JWT_SECRET_KEY` in Render (logs everyone out), and review Admin → audit events for the business |

## 6. Honest expectations to give testers

* Early software with rough edges. Some pages will be slow on first load.
* Email/WhatsApp are not fully working yet.
* It's a bookkeeping aid, not accounting or tax advice.
* They should keep their own records alongside it for the whole beta.

## 7. Legal and privacy (decide before inviting)

* The Terms and Privacy pages are **drafts**, labelled as such. For real
  businesses entering real data, have them reviewed before the beta if you can.
* Tell testers plainly what you store (their business records and account
  email), where (a managed database; encrypted daily backups for 30 days), who
  can see it (you as platform admin; their own team by role), and how to ask for
  deletion.
* Don't ask for bank details, card numbers or passwords - ever.

## 8. Ending the beta (or a tester's part in it)

* Offer each tester a copy of their data (a CSV/PDF export from the app) before
  you delete anything.
* Delete on request: Admin → Businesses → Delete, then Users → Delete. Backups
  roll off after 30 days; say so.
* Thank them, and tell them what changed because of their feedback.
