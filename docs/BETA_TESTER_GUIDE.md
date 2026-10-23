# Tallyra private beta - tester guide

Thank you for helping test Tallyra. This guide takes you from your first
login to a full week of use. The owner of the beta ({{your_name}},
{{support_email}}) will set up the first session with you.

## What this is (and isn't)

Tallyra is a **bookkeeping and reporting assistant** for small businesses that
keep their books in spreadsheets today. You record sales, expenses and
purchases; it shows you profit, who owes you money, and what is running low,
and an AI assistant answers questions about *your* numbers.

It is **early software**, in a **free, supervised beta**. It is not a
replacement for an accountant, and you should **keep your original spreadsheets
and receipts** for the whole beta - part of your job is to check that
Tallyra's figures match them.

### Ground rules

* Don't enter bank logins, card numbers or passwords anywhere in the app.
* Start with **sample or a small slice of real data** (one month), not your
  whole history.
* If something looks wrong, **tell us, don't work around it** - that is the
  most useful thing you can do.

## 1. Getting in

1. You'll get an invitation email from the owner. Sign-up only works for the
   **email address that was invited**.
2. Go to the app, press **Create account**, and use that same email. Choose a
   strong password.
3. Creating an account does **not** log you in. Go to **Log in** and sign in.
4. The first time, a short setup asks for your business name (and a few
   optional details such as country and currency). Currency is **US dollars
   only** for now.

> Tip: the first request after the app has been idle can take 30-60 seconds
> while the free server wakes up. If a page seems stuck for a minute, press
> **Retry** or reload.

## 2. Your first session (about 45 minutes, with the owner)

Work through these in order. After each step, compare with your spreadsheet.

| # | Do this | Where | You should see |
|---|---|---|---|
| 1 | Add 2-3 **customers** (or import a CSV, step 8) | Customers → New | They appear in the list |
| 2 | Add a **vendor** you buy from | Vendors → New | Needs a US tax ID (EIN) and an address. If you don't have one, skip - you can type a vendor name when recording a purchase |
| 3 | Record a **sale** with 2 line items | Sales → New | Totals add up; status "unpaid" |
| 4 | Record a **payment** on it (part, then the rest) | Open the sale → Record payment | Status goes partially paid → paid; you can't pay more than is owed |
| 5 | Record an **expense** | Expenses → New | It appears in the list |
| 6 | **Scan a receipt**: on the new-expense form, choose a photo or PDF of a receipt | Expenses → New → scan control | The form pre-fills vendor, amount and date. **Nothing is saved until you press save** - check the amount |
| 7 | **Scan a supplier bill** and add it to stock (see section 3) | Purchases → Scan a bill | A pop-up listing every item and count |
| 8 | **Import a CSV** of customers, products, vendors or expenses | Data Upload | A preview and column-matching step, then a result with any rows that had problems |
| 9 | Look at the **Dashboard** and **Reports** | Overview, Reports | Sales, expenses, profit and money owed for the period; Reports can download a PDF |
| 10 | Ask the **AI Assistant** a few questions | AI Assistant | See section 5 |

## 3. Scanning a bill and adding it to stock

1. Go to **Purchases** and press **Scan a bill**.
2. Choose a photo (JPG, PNG, WebP) or a PDF, up to 3 MB.
3. A pop-up lists every item it found with its **count**, unit cost and total,
   plus the bill number, date and tax. You can **edit any value, remove a row,
   or add a row**. A warning appears if the items don't add up to the total
   printed on the bill - compare with the paper.
4. **Type the vendor name** yourself (it suggests your saved vendors).
5. Optional: tick **Also add these counts to my stock**. For each item choose
   an existing product, or **+ New product** (you give it a SKU and a selling
   price), or leave it out.
6. Press **Confirm**. One purchase is recorded with all the items you left in.
   Nothing is saved before that; **Esc** or **Cancel** throws the scan away.

Good to know:

* A purchase that added stock is marked **added to stock**. Its items are then
  **locked** (you can still change the vendor, date, tax and notes).
* **Voiding** it takes that stock back out. If some of it has already been used
  or sold, the void is refused and tells you what to adjust first.
* The original photo/PDF is **not kept** - keep your paper or file copy.
* Scans use a free AI service with a usage limit. If it says the scanner is
  busy, wait about a minute and try again.

## 4. Your team

**Settings → Team**: the owner or an admin can add people who already have a
Tallyra account (they must have been invited to the beta too). Roles:

| Role | Can do |
|---|---|
| Owner | Everything, including the plan |
| Admin | Everything except change the owner or the plan |
| Accountant | Record and edit data, import, export reports |
| Viewer | Look only - no editing, importing or exporting |

The free plan allows 2 people; the owner can change the plan in Settings (no
payment is taken during the beta).

## 5. The AI Assistant and insights

* It can answer questions such as "What are my total sales?", "What's my
  biggest expense?", "Who owes me money?", "What's low on stock?".
* The **figures come from the system's own calculations**, not guesswork. If you
  don't name a period it uses *all time* and says so.
* It can only **read** your data. It cannot create, change, delete or send
  anything, and it will say so if asked.
* It can still **word things badly**. Please report any answer that
  contradicts your numbers - include the question and what you expected.

## 6. Every week during the beta

1. Pick one real week or month of your spreadsheet and enter it.
2. **Reconcile**: do the Dashboard's sales, expenses and profit match your
   spreadsheet for the same period? Note any difference, however small.
3. Try one thing you'd really do (a customer paying late, a stock count, a
   month-end report).
4. Fill in the short feedback form the owner sends (10 minutes).

## 7. Known limits (please don't report these as bugs)

* Email and WhatsApp sending are in test mode: reports sent to other people may
  not arrive, and team invitations are not emailed.
* Billing isn't connected; currency is USD only.
* Stock changes only through scanned bills you add to stock or manual
  adjustments - **sales don't reduce stock automatically**.
* The server sleeps when idle, so the first load can be slow.
* Imports are limited to 5 MB / 3,000 rows (about a minute for the largest).
* Terms and Privacy pages are drafts.

## 8. Reporting a problem or an idea

Email {{support_email}} with:

* **What you were doing** (the page and the steps)
* **What you expected** and **what happened** (copy any red error message)
* **A screenshot**, if you can - blur anything private
* **Roughly when** it happened

For a wrong number, add the figure you expected and where it came from (e.g.
"my spreadsheet, cell D14").

## 9. Your data

* You can ask at any time for your business and its data to be **deleted**; the
  owner will confirm when it is done.
* Daily encrypted backups are kept for 30 days.
* At the end of the beta you can keep using the app or have everything removed.
