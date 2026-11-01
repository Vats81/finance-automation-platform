# Private beta - accounting and bookkeeping firms

**Nothing in this file has been sent, and nothing will be sent by the app.** These are
drafts for the owner to edit and send personally, to firms the owner has chosen, when the
owner decides. Read "Before the first message" first.

Placeholders: `{{first_name}}`, `{{firm_name}}`, `{{your_name}}`,
`{{beta_link}}` (the unlinked `/beta` interest form).

## What a firm is being asked to try

A firm gets a workspace where it keeps its clients' books in one place: each client is a
business, staff have roles (owner, admin, accountant, viewer), and the firm sees all clients'
revenue, expenses, profit and receivables in one overview. Clients can be imported from the
spreadsheets the firm already receives (CSV), and bills and receipts can be scanned.

It is early software. It is **not** a replacement for the firm's accounting system or
professional judgement, and the firm should keep its existing records for the whole beta,
because checking that Finverlo's figures match them is the point.

## What we are asking for, and what we are not

**We ask for:** a few minutes of honest feedback each week, and a willingness to try the real
workflow on a small scale.

**The "data" request, stated plainly.** Start with **the firm's own books or sample data, or
one client who has agreed**. Do not ask any firm to upload several real clients' records on day
one. Instead ask for:

1. **The layout of the spreadsheets they receive** (column names and a few made-up rows), so
   the import can be tested against how clients really send things.
2. **One willing client**, with that client's agreement, before any real client data goes in.
3. **The reports they produce every month** (what the client sees), so we build the ones that
   matter.

Never ask for bank logins, statements, tax IDs or anything that identifies a client's
customers. The terms already say a firm confirms it is authorised by each client; keep that
true by asking for one client at a time.

## Before the first message (do these first)

- [ ] `REGISTRATION_REQUIRES_INVITE=true` is set in Render, so only people you invite can sign up.
- [x] The support email is `support@finverlo.com` (forwarded to you, tested).
- [ ] **Email actually delivers**: the Resend sending domain `finverlo.com` is verified. Until then,
      invitations and "forgot password" emails will not arrive (Admin -> Users -> Reset password is
      the fallback).
- [ ] The `[QA]` test data is gone (`python backend/scripts/purge_qa_data.py`, preview, then `--apply`).
- [ ] You have clicked through the firm screens yourself once (create a firm, add a client, invite
      staff, open a client, import a CSV, Plan & billing).
- [ ] The restore drill has run once, so a backup is proven restorable.
- [ ] You have decided whether firms are charged during the beta (the default is no: beta mode, no
      payment taken, plans only set limits).

## Who to ask first

Small firms of 1-10 people who already keep several small clients' books in spreadsheets or a
patchwork of tools. Ask 3-5 firms, not 30. One person who does the day-to-day bookkeeping is
more useful than a partner who will never log in.

Good first conversations are with people you already know, or who found you.

## 1. Short note to a firm you know

> Subject: Would you try a tool for keeping several clients' books in one place?
>
> Hi {{first_name}},
>
> I'm building Finverlo, a bookkeeping and reporting tool aimed at small firms that look after
> several small clients, many of them still sending spreadsheets. Each client gets its own books,
> your staff get roles, and you see every client's revenue, expenses and profit in one view.
>
> It's early, so I'm running a free, hands-on beta with just a few firms, and {{firm_name}} came to
> mind. I'd set it up with you. I'd ask for a few minutes of honest feedback a week, and to start
> with your own books or one client who's happy to be involved, not a pile of real client files.
>
> If you're curious, register interest here: {{beta_link}}. That only registers interest; it
> doesn't create an account. No problem at all if it's not for you.
>
> {{your_name}}

## 2. Post in a community of bookkeepers or accountants (only where it is allowed)

> Looking for 3-5 small bookkeeping or accounting firms to try a free, private beta of a tool for
> keeping several clients' books in one place: client overview, staff roles, CSV import, bill
> scanning. It's early software and I'll set it up with you. In return I'd like a few minutes of
> honest feedback a week. Register interest (interest only, no account, no client data):
> {{beta_link}}

## 3. Reply to a firm that registered interest

> Subject: Thanks for your interest in the Finverlo beta
>
> Hi {{first_name}},
>
> Thanks for registering. I'm taking firms in small batches so I can set each one up properly, so
> this isn't an invitation yet. To help me decide, could you tell me:
>
> 1. Roughly how many clients you look after, and how they send you their numbers (spreadsheets,
>    bank exports, an app)?
> 2. What you produce for them each month, and what takes the most time?
> 3. How many people on your team would use it?
>
> Please don't send any client or bank details. The layout of a typical spreadsheet with made-up
> numbers is plenty.
>
> {{your_name}}

## 4. Invitation to a firm you have chosen

Move them to **Invited** in Admin -> Beta waitlist, then click **Send invitation email** on
their row. The message below is the suggested text (a firm gets this version, anyone else gets a
shorter business one). You can edit the subject and the message, and nothing is sent until you
confirm. It goes from `noreply@finverlo.com` with replies to `support@finverlo.com`, the row then
shows "Invitation sent <date>", and a second send needs a deliberate "send again".

> Subject: Your place in the Finverlo beta
>
> Hi {{first_name}},
>
> I'd like to invite {{firm_name}} to the beta. Here is how it will go:
>
> 1. Sign up at https://www.finverlo.com/app/signup with this email address, then choose
>    "I run an accounting or bookkeeping firm".
> 2. Add one client to start: your own books or one client who has agreed. Import their
>    spreadsheet, and compare the totals with what you already have.
> 3. Invite a colleague if you like (they sign up first, then you add them with their email).
> 4. Keep your existing records. Tell me about anything that doesn't match, however small.
>
> It's free during the beta and no payment details are involved. I'll check in once a week, and
> there's a short tester guide at https://www.finverlo.com/beta. For anything urgent or odd,
> write to support@finverlo.com.
>
> Thank you for helping,
> {{your_name}}

## 5. If a firm declines or goes quiet

> No problem at all, and thanks for considering it. If it ever becomes useful, you're welcome to
> get back in touch.

Do not follow up more than once. Never message a firm that has not heard from you first or
registered interest.

## What to learn from each firm (one short call a week)

- Did the totals match their own records? Which didn't, and by how much? (Top priority.)
- How long did importing one client take, and where did it get stuck?
- What do they still do outside Finverlo every month, and why?
- Would they put a second client in? A third? What would stop them?
- Would they pay for it, and roughly what feels fair per client or per month? Ask this only in
  week 3 or 4, once they have used it.

## Pricing conversation

The product's plans are Free (2 clients, 2 staff), Growth (15 clients, 5 staff) and Practice
(50 clients, 15 staff). The prices are not set in the product; they live in Stripe. Do not quote
a price to a firm until you have set one. Ask what feels fair first.
