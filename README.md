# Blood Bank & Donor Management System

A college mini-project that connects blood donors, people searching for blood, and blood bank administrators in one system.

## Problem Statement

Finding a compatible blood donor quickly, and giving blood banks a clear view of inventory and incoming requests, is still a largely manual, fragmented process in many places. This project prototypes a web application that brings donor registration, a searchable donor directory, blood inventory tracking, request handling, and basic reporting into a single, easy-to-use interface.

## Objectives

- Let volunteers register as blood donors with their blood group and location.
- Let the public search for donors or submit blood requests.
- Give administrators a dashboard to monitor donors, inventory, and requests.
- Provide simple reports summarizing donations, inventory, and requests.
- Build the system incrementally: a working frontend first, then a real backend, database, and authentication.

## Current Implementation Status: Step 5 — Final Testing & Local Setup (Complete)

Step 1 delivered a frontend prototype with fictional, client-side-only data. Step 2 added a real Flask backend, SQLite database, and authentication. Step 3 made the donor directory and blood inventory real and database-backed. Step 4 wired up real blood-request submission/approval/fulfilment (with transactional inventory deduction), a real admin dashboard, and real reports with CSV export. **Step 5 is final testing, a small security hardening pass, and this README being brought up to a standard where someone else can clone the repo onto their own Windows machine and get it running from scratch.** No new features were added in this step — see **Planned Development Stages** below for the full picture.

What Step 4 delivered (still true, unchanged by Step 5):
- **Blood requests** (`pages/requests.html`): any logged-in user can submit a request and see their own request history; administrators can search/filter/inspect every request and move it through `Pending → Approved → Fulfilled` or `→ Rejected` (rejection requires a reason). All of this is enforced server-side — a regular user can never view or act on someone else's request, and only an admin can change a status.
- **Inventory integration:** approving a request checks that enough *usable* (active, unexpired) stock exists; fulfilling one actually deducts it, earliest-expiring batch first, inside a single database transaction with the request's status change — if the deduction fails, nothing is committed, so inventory and the request are left exactly as they were. A second "fulfill" click on an already-fulfilled request is rejected by the status-transition check before it can touch inventory again, so stock is never double-deducted; stock quantities are clamped so they can never go negative.
- **Admin dashboard** (`pages/admin.html`): every statistic — total donors, available units, pending/approved/fulfilled requests, per-blood-group stock, recent requests, low-stock/expiry alerts — comes from `GET /api/admin/summary`, computed from the database on every request.
- **Reports** (`pages/reports.html`, admin-only): inventory summary, a request-status breakdown with a selectable date range, and a donation summary, all from real data, plus one-click CSV export for the requests and donations reports (generated on the backend from the same authorized, filtered queries — never a plain list of raw database rows, and donor contact details are never included in a donation export).

What Step 5 actually changed:
- Ran the full automated suite and a from-scratch "fresh laptop" simulation (new database, new `.env`, new admin account, new user registration, full request → approve → fulfil → dashboard → report → CSV walk-through) end to end — see **Running the Tests** and the test results reported alongside this change.
- Replaced two internal `assert`-based column-whitelist checks in `backend/models.py` with explicit `raise ValueError(...)` — `assert` is silently removed when Python runs with the `-O` flag, so it was never a reliable safety boundary; this closes that theoretical gap without changing any observable behavior (both were unreachable with attacker-controlled input even before the fix, since callers only ever pass hardcoded, already-whitelisted keys).
- Removed `debug=True` from the unused direct-run fallback in `backend/app.py` (`python -m backend.app`) so an interactive debugger/traceback can never be exposed, even accidentally; the documented `flask --app backend.app run` command was never affected.
- Added the two optional inventory-threshold variables to `.env.example` that were already read by `backend/config.py` but not documented there.
- Rewrote the README's setup instructions to be copy-paste-accurate for a fresh Windows machine (verified command-by-command against this codebase), added **Stopping and restarting** and **Troubleshooting common setup errors**, and removed a redundant "cloning" section that duplicated step 1 of Setup.

Nothing from Steps 1–4 was rewritten or redesigned to do this — the existing auth/session/CSRF/role-based-authorization system, SQLite setup, and every endpoint are unchanged in behavior.

## Architecture

```
Browser (Step 1 HTML/CSS/JS, served by Flask)
        │  fetch() JSON requests, same-origin
        ▼
Flask app (backend/app.py)
  ├─ backend/auth.py       — /api/auth/* : register, login, logout, me, CSRF token
  ├─ backend/admin.py      — /api/admin/* : admin dashboard summary (role enforced server-side)
  ├─ backend/donors.py     — /api/donors/* : directory, profile, donation history
  ├─ backend/inventory.py  — /api/inventory/* : public summary + admin batch management
  ├─ backend/requests.py   — /api/requests/* : submission, viewing, admin status transitions
  ├─ backend/reports.py    — /api/reports/* : admin-only summaries + CSV export
  ├─ backend/models.py     — parameterized SQL data access (no ORM)
  ├─ backend/validators.py — shared validation constants (blood groups, statuses, transitions, ...)
  └─ backend/database.py   — SQLite connection + schema + additive migrations (instance/bloodbank.db)
```

Flask serves both the existing static frontend (`index.html`, `pages/`, `assets/`) **and** the JSON API from a single process, so there is no CORS configuration and no second server to run.

## Technology Stack

| Layer | Technology |
|---|---|
| Structure | HTML5 (semantic markup) |
| Styling | CSS3, [Bootstrap 5.3](https://getbootstrap.com/) (via CDN) |
| Icons | [Bootstrap Icons 1.11](https://icons.getbootstrap.com/) (via CDN) |
| Frontend behaviour | Vanilla JavaScript (ES6+), no framework or build step |
| Backend | Python 3.11+ (tested on 3.14), [Flask 3](https://flask.palletsprojects.com/) |
| Sessions | [Flask-Session](https://flask-session.readthedocs.io/) (server-side, filesystem-backed) |
| CSRF protection | [Flask-WTF](https://flask-wtf.readthedocs.io/) `CSRFProtect` |
| Password hashing | Werkzeug's `generate_password_hash` / `check_password_hash` (PBKDF2) |
| Database | SQLite (file-based, no server process; original synopsis specified MySQL — pending mentor approval) |
| Testing | pytest + Flask's test client, isolated temporary SQLite databases |
| Version control | Git & GitHub |

**External CDN dependency notice:** the frontend loads Bootstrap 5, Bootstrap Icons, and their JavaScript bundle from `cdn.jsdelivr.net`. An internet connection is required the first time each page loads (browsers cache the files afterward). No application code or user data is sent to these CDNs — they only serve static CSS/JS/font files.

## Project Directory Structure

```
Blood Bank Management System/
├── index.html                 # Landing page
├── pages/
│   ├── login.html              # Login form, connected to the backend
│   ├── register.html           # Donor registration form, connected to the backend
│   ├── donors.html             # Searchable donor directory — real SQLite data (Step 3)
│   ├── inventory.html          # Blood inventory overview + admin batch panel — real data (Step 3)
│   ├── requests.html           # Submit/view requests + admin processing — real data (Step 4)
│   ├── admin.html               # Administrator dashboard — real data (Step 4)
│   └── reports.html            # Reports + CSV export, admin-only — real data (Step 4)
├── assets/
│   ├── css/
│   │   └── style.css           # Shared custom styles
│   ├── js/
│   │   ├── main.js             # Shared interactive behaviour (nav, validation, password toggles)
│   │   ├── mock-data.js        # Fictional demo data (blood-group list reused for filter dropdowns only)
│   │   ├── auth.js             # Talks to the backend: session-aware nav, login/register forms
│   │   ├── donors.js           # Donor directory search/filter/pagination + detail modal
│   │   ├── inventory.js        # Inventory summary/alerts + admin batch management panel
│   │   ├── requests.js         # NEW — request submission, "my requests", admin processing panel
│   │   ├── admin-dashboard.js  # NEW — real admin dashboard statistics
│   │   └── reports.js          # NEW — reports (date range, CSV export)
│   └── images/
│
├── backend/                   # Flask application
│   ├── app.py                   # create_app(), serves the frontend + registers API blueprints
│   ├── config.py                 # Config / TestConfig, loaded from environment variables
│   ├── database.py               # SQLite connection, schema, and additive migrations
│   ├── models.py                  # Parameterized SQL data-access functions
│   ├── validators.py              # Shared validation constants (blood groups, statuses, transitions, ...)
│   ├── auth.py                    # /api/auth/* routes + login_required / admin_required decorators
│   ├── admin.py                   # /api/admin/* routes (admin dashboard summary)
│   ├── donors.py                  # /api/donors/* routes
│   ├── inventory.py               # /api/inventory/* routes
│   ├── requests.py                # NEW — /api/requests/* routes
│   └── reports.py                 # NEW — /api/reports/* routes (JSON + CSV export)
│
├── database/                  # One-off scripts, not imported by the app at request time
│   ├── init_db.py               # Creates the database/tables if missing + runs migrations (idempotent)
│   ├── seed_data.py              # Inserts fictional donors/inventory/requests/donations (idempotent)
│   └── create_admin.py           # Provisions a local admin account from .env (not a public API)
│
├── tests/                      # Automated backend tests (pytest)
│   ├── conftest.py               # Shared fixtures: app/client/admin_client/registered_user/...
│   ├── test_auth.py
│   ├── test_database.py
│   ├── test_donors.py
│   ├── test_inventory.py
│   ├── test_requests.py          # NEW
│   ├── test_admin_dashboard.py   # NEW
│   └── test_reports.py           # NEW
│
├── instance/                   # Gitignored — bloodbank.db + session files live here
├── .venv/                      # Gitignored — Python virtual environment
├── requirements.txt
├── .env.example                 # Copy to .env and fill in real values
├── README.md
└── .gitignore
```

## Setup and Local Execution (Windows)

**Prerequisites:** Python 3.11 or later (this project was built and tested on 3.14) and Git. No MySQL/Postgres server, Node.js, or internet-facing deployment is required.

### 1. Clone the repository

```bash
git clone <repository-url>
cd "Blood Bank Management System"
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your environment

```bash
copy .env.example .env
```

Then edit `.env` and set:
- `FLASK_SECRET_KEY` — generate one with `python -c "import secrets; print(secrets.token_hex(32))"`. This signs session cookies and CSRF tokens; never share it or commit it.
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_NAME` — only used by the admin-provisioning script in step 6 below.

`.env` is listed in `.gitignore` and must never be committed.

### 5. Initialize (or update) the database

```bash
python database/init_db.py
```

This creates `instance/bloodbank.db` and all tables if they don't exist yet. If you have a database from an earlier step, this also safely **migrates** it in place — it adds the columns Step 3 (`donors.email`, `donors.updated_at`, `blood_inventory.status`, `blood_inventory.notes`) and Step 4 (`blood_requests.rejection_reason`, `blood_requests.decided_by`, `blood_requests.fulfilled_at`) introduced, with `ALTER TABLE ... ADD COLUMN`, and only for columns that are actually missing. It never drops a table, never deletes a row, and is safe to run every time the app starts (`backend/app.py` also calls it automatically on `create_app()`).

### 6. Load demonstration data (optional but recommended)

```bash
python database/seed_data.py
```

Inserts fictional donors (with varied statuses), multi-batch inventory per blood group — including a deliberate low-stock example, a near-expiry batch, and an expired batch, all computed relative to today's date so they stay meaningful — plus blood requests and donation records. Safe to re-run: it skips any table that already has rows, so it never duplicates data or touches records you've since created or edited through the app.

### 7. Provision a local administrator account

```bash
python database/create_admin.py
```

Reads `ADMIN_EMAIL`/`ADMIN_PASSWORD`/`ADMIN_NAME` from `.env` and creates (or promotes) that account to the `admin` role. There is no public sign-up path to the `admin` role — this script, run with local shell access, is the only way to create one.

### 8. Start the backend

```bash
python -m flask --app backend.app run
```

### 9. Open the application

Visit **http://127.0.0.1:5000/** in a browser. Flask serves the existing frontend pages directly, so there is nothing else to start — `index.html`, every page under `pages/`, and the `/api/...` endpoints are all served by this one process.

Log in with the administrator credentials from step 7 to reach `pages/admin.html`, or register your own new account via `pages/register.html` to test the regular donor flow.

### Stopping and restarting

To stop the server, go to the terminal it's running in and press `Ctrl+C`. Your data is untouched — it's saved in `instance/bloodbank.db` on disk, not held in memory — so the next time you want to use the app, you only need to repeat **step 8** (`python -m flask --app backend.app run`) from inside the activated virtual environment; steps 1–7 are one-time setup and don't need to be repeated. If you open a new terminal, remember to re-activate the virtual environment first (step 2's second command, `.venv\Scripts\activate`) before starting the server again.

### Troubleshooting common setup errors

| Problem | Likely cause / fix |
|---|---|
| `'flask' is not recognized` / `ModuleNotFoundError: No module named 'flask'` | The virtual environment isn't activated (or dependencies weren't installed into it). Re-run step 2's activation command, confirm your prompt shows `(.venv)`, then re-run step 3. |
| PowerShell: activation does nothing, or `running scripts is disabled on this system` | PowerShell's script-execution policy is blocking `Activate.ps1`. Either use `.venv\Scripts\activate` (the `.bat` version, which this README uses and isn't affected), or run Command Prompt (`cmd.exe`) instead of PowerShell for these steps. |
| `OSError: [Errno 98]` / `OSError: [WinError 10048]` — address already in use | Another process (often a previous server you forgot to stop) is already listening on port 5000. Stop it (`Ctrl+C` in its terminal, or close that terminal), or run this one on a different port: `python -m flask --app backend.app run --port 5050`. |
| Login/register always fails with a CSRF or "Bad request" error | Normal browser use is unaffected (`assets/js/auth.js` fetches a token automatically). This only happens when scripting the API directly (e.g. `curl`) without first `GET`-ting `/api/auth/csrf-token` and sending it back as the `X-CSRFToken` header — see **API Endpoints** below. |
| `sqlite3.OperationalError: database is locked` | Another process still has `instance/bloodbank.db` open — close any other running copy of this app (including a previous server you forgot to stop) and try again. |
| Running `database/init_db.py` or `database/seed_data.py` does nothing visible / says rows already exist | That's expected and correct, not an error — both scripts are idempotent and skip tables that already have data, so re-running them after the first time is always safe and simply confirms nothing changed. |
| `.env` changes don't seem to take effect | The running server read `.env` at startup. Stop it (`Ctrl+C`) and start it again (step 8) after editing `.env`. |
| Admin login fails after running `create_admin.py` | Double-check `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env` match exactly what you're typing into the login form, and that you re-ran `python database/create_admin.py` *after* saving those changes to `.env`. |

## API Endpoints

All endpoints return JSON. State-changing requests (`POST`/`PATCH`) require the `X-CSRFToken` header, obtained from `GET /api/auth/csrf-token`; `assets/js/auth.js` handles this automatically for the frontend.

### Authentication (Step 2)

| Method & Path | Purpose | Auth required |
|---|---|---|
| `GET /api/auth/csrf-token` | Issue a CSRF token for the current session | No |
| `POST /api/auth/register` | Create a new account (always role `user`) + donor profile | No |
| `POST /api/auth/login` | Verify credentials, start a server-side session | No |
| `POST /api/auth/logout` | End the current session | Yes |
| `GET /api/auth/me` | Return the current user's id, name, email, role | Yes |
| `GET /api/admin/summary` | Full admin dashboard summary (Step 4): donor/inventory/request counts, per-blood-group stock, recent requests, low-stock/expiry alerts | Yes, role `admin` |

**Roles:** `user` (default for every public registration) and `admin` (provisioned only via `database/create_admin.py`, never self-assignable through the API — the register endpoint ignores any `role` field a client sends).

### Donors (Step 3)

| Method & Path | Purpose | Auth required |
|---|---|---|
| `GET /api/donors` | Search/filter the directory (`q`, `bloodGroup`, `city`, `status`, `email`, `phone`, `limit`, `offset`) | No (contact fields hidden unless owner/admin) |
| `GET /api/donors/<id>` | One donor's permitted details | No (same privacy rule as above) |
| `POST /api/donors` | Complete your own donor profile (one per account; 409 if you already have one) | Yes |
| `PATCH /api/donors/<id>` | Update permitted fields; only the owner or an admin can edit; only an admin can change `status` | Yes |
| `GET /api/donors/<id>/donations` | That donor's donation history | Yes, owner or admin |

Anonymous and other users only ever see `id`, `fullName`, `bloodGroup`, `city`, `status`, `lastDonationDate`, `createdAt`. `phone`, `email`, `userId`, `consentGiven`, and `updatedAt` are included only when the requester is that donor's own account or an administrator — enforced server-side on every request, not by hiding fields in the UI.

### Inventory (Step 3)

| Method & Path | Purpose | Auth required |
|---|---|---|
| `GET /api/inventory/summary` | Per-blood-group usable/total/expired/near-expiry totals + low-stock/out-of-stock alerts | No |
| `GET /api/inventory` | List raw batches (optional `bloodGroup`, `status` filters) | Yes, role `admin` |
| `GET /api/inventory/<id>` | One batch's details | Yes, role `admin` |
| `POST /api/inventory` | Create a new stock batch | Yes, role `admin` |
| `PATCH /api/inventory/<id>` | Correct a batch (quantity, dates, notes) or archive it (`status: "archived"`) | Yes, role `admin` |

The public summary is read-only and aggregate-only (no batch-level detail); creating, editing, listing, and archiving batches all require an authenticated administrator, enforced by `@admin_required` on the server.

### Blood requests (Step 4)

| Method & Path | Purpose | Auth required |
|---|---|---|
| `POST /api/requests` | Submit a blood request (always starts `Pending`) | Yes |
| `GET /api/requests` | List requests (`status`, `bloodGroup`, `dateFrom`, `dateTo`, `limit`, `offset`; admins can also pass `q`) | Yes (a regular user only ever sees their own, regardless of filters) |
| `GET /api/requests/<id>` | One request's details | Yes, owner or admin |
| `PATCH /api/requests/<id>` | Change status: `Approved`, `Rejected` (`rejectionReason` required), or `Fulfilled` | Yes, role `admin` |

Valid status transitions are `Pending → Approved/Rejected` and `Approved → Fulfilled/Rejected`; `Fulfilled` and `Rejected` are terminal. Approving checks that enough usable stock exists (without deducting it yet); fulfilling deducts it for real, earliest-expiring batch first, in the same database transaction as the status change — see **Blood Requests & Inventory Integration** below.

### Reports (Step 4, all admin-only)

| Method & Path | Purpose |
|---|---|
| `GET /api/reports/requests` | Status breakdown + filtered request list (`status`, `bloodGroup`, `dateFrom`, `dateTo`) |
| `GET /api/reports/requests/export` | Same, as a downloadable CSV |
| `GET /api/reports/donations` | Donation totals + list (`dateFrom`, `dateTo`) |
| `GET /api/reports/donations/export` | Same, as a downloadable CSV (donor name + blood group only — never phone/email) |

The inventory summary shown on the reports page reuses the existing public `GET /api/inventory/summary` rather than duplicating it.

## Database Schema

SQLite, foreign keys enforced (`PRAGMA foreign_keys = ON` on every connection). Timestamps are ISO-8601 UTC strings (e.g. `2026-10-29T12:34:56.789Z`); plain dates (`last_donation_date`, `collected_date`, `expiry_date`, `donation_date`) are ISO-8601 dates (`2026-10-29`). Full definitions are in `backend/database.py`. Columns marked **Step 3**/**Step 4** were added by an additive migration (see below) and did not exist in the original Step 2 schema.

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | Login accounts: name, normalized email (unique), password hash, role, status | — |
| `donors` | Donor profiles: blood group, contact, city, status, **email** *(Step 3)*, **updated_at** *(Step 3)* | `user_id` → `users.id` (nullable — a donor need not have a login account) |
| `blood_inventory` | Stock **batches** per blood group, with quantity, collection/expiry dates, **status** *(Step 3: `active`/`archived`)*, **notes** *(Step 3)* | — |
| `blood_requests` | Requests for blood: group, quantity, urgency, status, **rejection_reason** *(Step 4)*, **decided_by** *(Step 4)*, **fulfilled_at** *(Step 4)* | `user_id` → `users.id` (nullable), `decided_by` → `users.id` (the admin who last changed status) |
| `donations` | Individual donation records | `donor_id` → `donors.id` (`ON DELETE CASCADE`) |

`blood_inventory` was already batch-structured in Step 2 (one row = one batch, with its own `collected_date`/`expiry_date`), so Step 3 reused that structure rather than introducing a parallel schema — it only added `status` (so a batch can be archived instead of deleted) and `notes` (so an administrative correction can record a reason).

### Database migrations

`backend/database.py` defines `MIGRATIONS`: a small, explicit list of `ALTER TABLE ... ADD COLUMN` statements, each applied only if `PRAGMA table_info` shows the column is actually missing. `init_db()` — called both by `database/init_db.py` and automatically on every `create_app()` — runs these migrations *before* creating tables/indexes (since an index on a Step 3 column would otherwise fail against a Step 2 database), then backfills `donors.updated_at` from `created_at` for any pre-existing rows (SQLite's `ADD COLUMN` doesn't accept the computed timestamp default used elsewhere). This is additive and non-destructive: it only ever adds a column or fills in a null, never alters or drops anything, and is safe to run against a brand-new database (where the columns already exist) or an already-migrated one (where there's nothing left to do).

## Donor Management (Step 3)

- **Directory & search:** `pages/donors.html` searches/filters the real directory by name, blood group, city, and status, with server-side pagination (10 per page). All filtering happens in SQL with bound parameters (including escaping `%`/`_` in `LIKE` patterns), never by concatenating user input into a query.
- **Profile creation/updates:** registration (Step 2) still auto-creates a donor profile; `POST /api/donors` exists for the rarer case of a user without one (e.g. provisioned another way) and rejects a second profile for the same account with `409`. `PATCH /api/donors/<id>` lets a donor edit their own `fullName`/`email`/`bloodGroup`/`phone`/`city`/`lastDonationDate`; only an admin may also set `status`.
- **Status:** a small `pending` / `approved` / `rejected` set (already present in Step 2's schema), reused as-is — not a medical eligibility claim, just an administrative review state.
- **Donation history:** `GET /api/donors/<id>/donations` reads the real `donations` table and is restricted to that donor's own account or an admin; Step 3 only displays this history — recording new donations is Step 4 scope.
- **Privacy:** the directory and detail view never expose `phone`/`email`/`userId` to anyone except the donor themselves or an admin, regardless of how the request is made (verified by `tests/test_donors.py`, not just by what the UI shows).

## Blood Inventory (Step 3)

- **Batch tracking:** each `blood_inventory` row is one batch (blood group, quantity, collected/expiry dates, status, notes) — Step 2's existing structure, extended rather than replaced.
- **Stock summary:** `GET /api/inventory/summary` (public) sums *active* batches per blood group into `totalRecordedUnits`, `usableUnits`, `expiredUnits`, and `nearExpiryUnits`. Expired units are excluded from `usableUnits` but still counted in `totalRecordedUnits`, so stock is never silently "lost" from the books.
- **Alerts:** a blood group is `lowStock` when `0 < usableUnits < INVENTORY_LOW_STOCK_THRESHOLD` (default **10** units) and `outOfStock` when `usableUnits == 0`. A batch is `near_expiry` when its `expiry_date` is today or later but within `INVENTORY_NEAR_EXPIRY_DAYS` (default **7** days); both are configurable via `.env`. All of this is computed server-side in `backend/models.get_inventory_summary()` and covered by tests — the frontend only displays the numbers it's given.
- **Admin batch management:** the inventory page shows an admin-only panel (visible only when `GET /api/auth/me` reports role `admin`) to add a batch or archive one. Archiving sets `status = 'archived'` — batches are never deleted, so history and foreign-key integrity (e.g. `donations`) are preserved.
- **Unit of measure:** "units", matching the unit Step 1/2 already used — not switched to millilitres, since the project already had a working convention.
- **Request-driven deduction:** Step 3 only let an admin add/correct/archive batches directly. Step 4 (below) adds the other way stock changes: automatically, when a blood request is fulfilled.

## Blood Requests & Inventory Integration (Step 4)

- **Submission:** any authenticated user can submit a request (blood group, quantity 1–20, location, urgency, requester name/contact, optional notes); it always starts `Pending` with a unique id and creation timestamp.
- **Visibility:** a regular user's `GET /api/requests` and `GET /api/requests/<id>` only ever return *their own* requests — the `user_id` filter is applied server-side regardless of what query parameters are sent, and requesting another user's request by id returns `403`. Administrators see everything and can search/filter by status, blood group, requester name, and date range.
- **Status transitions:** `Pending → Approved` or `Rejected`; `Approved → Fulfilled` or `Rejected`; `Fulfilled` and `Rejected` are final. Any other transition (e.g. `Pending → Fulfilled` directly, or anything from a terminal state) is rejected with `409`, enforced against `backend/validators.REQUEST_TRANSITIONS` — the single source of truth for what's allowed, checked on the server regardless of what the UI shows as clickable.
- **Rejecting** requires a non-empty `rejectionReason` (`400` without one), recorded on the request.
- **Approving** checks that enough *usable* stock exists for the blood group (active batches, not expired) and refuses with `409` if not — this doesn't touch inventory yet, it just stops an admin from approving something unfulfillable.
- **Fulfilling** is the one step that actually moves stock: `backend/models.deduct_stock_for_request()` draws from active, unexpired batches **earliest-expiry-first**, and `backend/requests.py` wraps that deduction and the request's status update in a single transaction — on any error (including insufficient stock discovered at this point) both are rolled back together, so a failed fulfilment never leaves inventory partially deducted or the request in an inconsistent state. Quantities are always clamped so a batch can never go negative.
- **No duplicate deduction:** fulfilling is only ever reachable from `Approved`; once a request is `Fulfilled` it's a terminal state, so repeating the action (a double click, a retried request) is rejected by the transition check *before* any inventory code runs — tested explicitly in `tests/test_requests.py::test_repeated_fulfill_action_does_not_double_deduct_stock`.
- **Not implemented (by design):** medical compatibility/crossmatching — this is an administrative prototype, not a substitute for qualified medical review.

## Running the Tests

```bash
pytest tests/ -v
```

Each test gets its own temporary SQLite database and session directory (via pytest's `tmp_path`), so running the suite never touches `instance/bloodbank.db` or your real data. As of this step, **119 tests pass**: the Step 2/3 baseline of 74 (registration, login/logout, `/me`, admin authorization, schema, persistence, donor/inventory search, authorization, and stock-alert logic) plus **45 new Step 4 tests**:
- `tests/test_requests.py` (28): creation/validation, visibility (own vs. all), status-transition rules, reject-reason requirement, approve-with-insufficient-stock rejection, successful fulfilment with stock deduction, FEFO batch ordering, transactional rollback on failed fulfilment, and no-double-deduction on a repeated fulfill action.
- `tests/test_admin_dashboard.py` (4): real counts reflecting the database, correct empty state with no data, and figures updating after an inventory change.
- `tests/test_reports.py` (13): access control, status/blood-group/date-range filtering, invalid/inverted date rejection, and CSV export content and headers (including that a donation export never includes donor contact details).

Beyond the automated suite, Step 5 also ran a full manual pass against a completely separate, newly-initialized database (a stand-in for a fresh install on someone else's machine): register a new account, log in, provision an admin account, add an inventory batch, submit a request, approve it, fulfil it (confirming the stock deduction), and pull the admin dashboard and a CSV report — all against data that didn't exist beforehand.

## Security Considerations

- Passwords are hashed with Werkzeug's PBKDF2-based `generate_password_hash`; plaintext passwords are never stored or logged.
- Sessions are server-side (Flask-Session, filesystem-backed under `instance/flask_session`); the browser only holds a signed, HttpOnly, `SameSite=Lax` cookie referencing the session.
- All state-changing requests are protected against CSRF via Flask-WTF.
- All SQL is parameterized (`?` placeholders) — no string-built queries.
- Login responses don't reveal whether a given email exists; invalid email and invalid password return the same generic error.
- Role checks happen server-side on every protected request by re-reading the user's role from the database — the frontend hiding a button is never the security boundary.
- Error handlers return generic JSON messages and never leak stack traces, file paths, or database details to the client.
- No permissive CORS is configured — the API is only reachable from the same origin that serves the frontend.
- `.env`, the SQLite database, and session files are all excluded from Git via `.gitignore`.
- Donor and inventory authorization is re-checked against the database on every request (ownership for donors, `role == 'admin'` for inventory/request/report writes) — a donor ID, request ID, or role value sent by the client is never trusted on its own.
- Request/inventory status transitions are validated against an explicit allow-list server-side (`backend/validators.REQUEST_TRANSITIONS`), not just hidden in the UI; stock deduction and the status change it belongs to are committed or rolled back together as one transaction.
- CSV exports are generated on the backend from the same authorized, filtered queries as the JSON report endpoints (never a raw table dump), and the donations export deliberately omits donor phone/email even though the requesting admin could view an individual donor's contact details one at a time elsewhere.
- Internal column-whitelist checks in `backend/models.py` use `raise ValueError(...)`, not `assert` — `assert` statements are stripped out when Python runs with the `-O` optimization flag, so they can't be relied on as a safety boundary even for an internal invariant.
- The app never enables Flask's debug mode on the documented run path (`flask --app backend.app run`); the unused `python -m backend.app` fallback was corrected to match, so an interactive in-browser debugger/traceback can't accidentally be exposed either way.
- Verified (not just assumed): no `.env`, SQLite database, session file, or other sensitive file has ever been committed, in the current tree or anywhere in the Git history (`git ls-files` / `git log --all --diff-filter=A`), and `.env.example` documents every variable the app actually reads with placeholder, non-secret values only.

## Current Limitations

- **No donation-recording or donor-approval workflow UI** — the app displays existing donation history and lets an admin change donor `status`, but there's no "record a new donation" or bulk-approval screen; intentionally out of scope.
- **No password-reset flow** ("Forgot password?" remains a disabled link).
- **No rate limiting** on login/registration/API attempts.
- **Donor/request search pagination is offset-based** (simple Previous/Next or a `limit`/`offset` query), not cursor-based — adequate at this prototype's scale.
- **No real-time updates** — dashboard and report figures are fetched on page load/filter-change, not pushed live as other users act.
- **Concurrency is not deeply tested** — the fulfilment transaction is correct for this prototype's single-admin, single-request-at-a-time usage pattern (SQLite itself serializes writes), but true concurrent-admin race conditions were not specifically load-tested.
- **Honesty note on "another machine" testing:** Step 5's fresh-install verification used a newly initialized database, a fresh `.env`, and a fresh admin account on *this same development machine* — not a literal second physical computer. The setup steps below were written and verified command-by-command against this codebase, but a true first run on different hardware may still surface something OS/environment-specific (see **Troubleshooting**) that this process didn't catch.

## Planned Development Stages

- **Step 1 — Frontend & project foundation** *(done)*: complete HTML/CSS/JS prototype with mock data.
- **Step 2 — Flask backend, database, and authentication** *(done)*: Flask API, SQLite database foundation, and real registration/login/logout/session/role-based access, connected to the existing login and registration pages.
- **Step 3 — Donor management and inventory** *(done)*: real, database-backed donor directory/search/profiles/donation history, and batch-tracked inventory with low-stock/expiry alerts and admin batch management.
- **Step 4 — Blood requests, dashboard, and reports** *(done)*: real request submission/approval/rejection/fulfilment wired to transactional inventory deduction, a fully data-driven admin dashboard, and reports with CSV export.
- **Step 5 — Final testing and local setup** *(this step)*: full regression + fresh-machine testing, a small security hardening pass (see above), and setup/troubleshooting documentation accurate enough for someone else to run this on their own Windows laptop with their own local database and admin account.

## Disclaimer

All donor names, contact details, blood group counts, inventory figures, and blood requests shown anywhere in this prototype are **fictional demonstration data**. They do not represent real people, real blood availability, or any real blood bank's inventory or requests.
