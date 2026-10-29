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

## Current Implementation Status: Step 3 — Donor Management & Blood Inventory

Step 1 delivered a frontend prototype with fictional, client-side-only data. Step 2 added a real Flask backend, SQLite database, and authentication. **Step 3 replaces the donor directory and blood inventory mock data with real, database-backed functionality**: searchable/filterable donor records, donor self-service profile updates, donation-history viewing, batch-level inventory tracking, and low-stock/expiry alerts — all enforced server-side.

What's real now (in addition to everything from Step 2):
- The donor directory (`pages/donors.html`) searches and filters real `donors` rows from SQLite — by name, blood group, city, and status — with pagination and a detail view.
- A donor's own account can complete/update their profile; only an administrator can change a donor's `status`. Both are enforced server-side, independent of what the UI shows.
- Donation history (`GET /api/donors/<id>/donations`) comes from the real `donations` table and is visible only to that donor's own account or an administrator.
- The inventory page (`pages/inventory.html`) shows real, batch-aggregated stock per blood group — usable vs. total-recorded vs. expired vs. near-expiry — calculated server-side, plus low-stock and expiry alerts.
- Administrators get an in-page panel on the inventory page to add new stock batches and archive existing ones (no destructive deletes), restricted by `@admin_required` on every endpoint.
- The homepage's blood-group chips and "registered donors"/"available units" stats now read live totals from the same APIs.

What's still fictional / not yet wired up (Step 4 scope):
- Blood request submission, approval, rejection, and fulfilment (`pages/requests.html`) still use Step 1's mock data; no stock is deducted for requests.
- The admin dashboard's (`pages/admin.html`) own widgets still show Step 1 mock data; a read-only `GET /api/admin/summary` endpoint exists and is tested, but the dashboard UI isn't wired to it yet.
- Reports (`pages/reports.html`) are still static mock data.

## Architecture

```
Browser (Step 1 HTML/CSS/JS, served by Flask)
        │  fetch() JSON requests, same-origin
        ▼
Flask app (backend/app.py)
  ├─ backend/auth.py       — /api/auth/* : register, login, logout, me, CSRF token
  ├─ backend/admin.py      — /api/admin/* : admin-only endpoints (role enforced server-side)
  ├─ backend/donors.py     — /api/donors/* : directory, profile, donation history
  ├─ backend/inventory.py  — /api/inventory/* : public summary + admin batch management
  ├─ backend/models.py     — parameterized SQL data access (no ORM)
  ├─ backend/validators.py — shared validation constants (blood groups, email/phone patterns, statuses)
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
│   ├── requests.html           # Submit / view blood requests (still mock data — Step 4)
│   ├── admin.html               # Administrator dashboard (requires real admin login; widgets still mock data)
│   └── reports.html            # Summary reports (print-friendly, still mock data — Step 4)
├── assets/
│   ├── css/
│   │   └── style.css           # Shared custom styles
│   ├── js/
│   │   ├── main.js             # Shared interactive behaviour (nav, validation, password toggles)
│   │   ├── mock-data.js        # Fictional demo data still used by requests.html/reports.html
│   │   ├── auth.js             # Talks to the backend: session-aware nav, login/register forms
│   │   ├── donors.js           # NEW — donor directory search/filter/pagination + detail modal
│   │   └── inventory.js        # NEW — inventory summary/alerts + admin batch management panel
│   └── images/
│
├── backend/                   # Flask application
│   ├── app.py                   # create_app(), serves the frontend + registers API blueprints
│   ├── config.py                 # Config / TestConfig, loaded from environment variables
│   ├── database.py               # SQLite connection, schema, and additive migrations
│   ├── models.py                  # Parameterized SQL data-access functions
│   ├── validators.py              # NEW — shared validation constants (blood groups, email/phone, statuses)
│   ├── auth.py                    # /api/auth/* routes + login_required / admin_required decorators
│   ├── admin.py                   # /api/admin/* routes (admin-only)
│   ├── donors.py                  # NEW — /api/donors/* routes
│   └── inventory.py               # NEW — /api/inventory/* routes
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
│   ├── test_donors.py            # NEW
│   └── test_inventory.py         # NEW
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

This creates `instance/bloodbank.db` and all tables if they don't exist yet. If you have a database from an earlier step, this also safely **migrates** it in place — it adds the columns Step 3 introduced (`donors.email`, `donors.updated_at`, `blood_inventory.status`, `blood_inventory.notes`) with `ALTER TABLE ... ADD COLUMN`, and only for columns that are actually missing. It never drops a table, never deletes a row, and is safe to run every time the app starts (`backend/app.py` also calls it automatically on `create_app()`).

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

Log in with the administrator credentials from step 7 to reach `pages/admin.html`, or register a new account via `pages/register.html` to test the regular donor flow.

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
| `GET /api/admin/summary` | Example admin-only endpoint (read-only counts) | Yes, role `admin` |

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

## Database Schema

SQLite, foreign keys enforced (`PRAGMA foreign_keys = ON` on every connection). Timestamps are ISO-8601 UTC strings (e.g. `2026-10-29T12:34:56.789Z`); plain dates (`last_donation_date`, `collected_date`, `expiry_date`, `donation_date`) are ISO-8601 dates (`2026-10-29`). Full definitions are in `backend/database.py`. Columns marked **Step 3** were added by an additive migration (see below) and did not exist in the Step 2 schema.

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | Login accounts: name, normalized email (unique), password hash, role, status | — |
| `donors` | Donor profiles: blood group, contact, city, status, **email** *(Step 3)*, **updated_at** *(Step 3)* | `user_id` → `users.id` (nullable — a donor need not have a login account) |
| `blood_inventory` | Stock **batches** per blood group, with quantity, collection/expiry dates, **status** *(Step 3: `active`/`archived`)*, **notes** *(Step 3)* | — |
| `blood_requests` | Requests for blood: group, quantity, urgency, status | `user_id` → `users.id` (nullable) |
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
- **Out of scope here:** deducting stock for a fulfilled blood request, and any request-approval workflow — both belong to Step 4.

## Running the Tests

```bash
pytest tests/ -v
```

Each test gets its own temporary SQLite database and session directory (via pytest's `tmp_path`), so running the suite never touches `instance/bloodbank.db` or your real data. As of this step, **74 tests pass**: the original 24 (registration, login/logout, `/me`, admin authorization, schema, persistence, seed idempotency) plus 27 new donor tests and 23 new inventory tests covering search/filter/pagination, profile-ownership authorization (including "changing the ID in the URL doesn't grant access"), donation-history privacy, batch validation (invalid blood group, non-positive quantities, malformed/inconsistent dates), multi-batch stock aggregation, expired-stock exclusion, low-stock/near-expiry/expired classification, archived-batch exclusion, and admin-only write enforcement.

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
- Donor and inventory authorization is re-checked against the database on every request (ownership for donors, `role == 'admin'` for inventory writes) — a donor ID or role value sent by the client is never trusted on its own.

## Current Limitations

- **Blood requests and reports still show Step 1's fictional mock data** (`pages/requests.html`, `pages/reports.html`) — connecting them to the database, including stock deduction on fulfilment, is Step 4 scope.
- **The admin dashboard's own widgets** (`pages/admin.html`) still render Step 1 mock data rather than calling `GET /api/admin/summary`, even though that endpoint is real, tested, and admin-protected — wiring the dashboard UI to it is Step 3/4 polish, not done here.
- **No donation-recording or donor-approval workflow UI** — Step 3 displays existing donation history and lets an admin change donor `status`, but there's no "record a new donation" or bulk-approval screen; that's intentionally left for a later step.
- **No password-reset flow** ("Forgot password?" remains a disabled link).
- **No rate limiting** on login/registration/API attempts.
- **Donor search pagination is offset-based** (simple Previous/Next), not cursor-based — adequate at this prototype's scale.

## Planned Development Stages

- **Step 1 — Frontend & project foundation** *(done)*: complete HTML/CSS/JS prototype with mock data.
- **Step 2 — Flask backend, database, and authentication** *(done)*: Flask API, SQLite database foundation, and real registration/login/logout/session/role-based access, connected to the existing login and registration pages.
- **Step 3 — Donor management and inventory** *(this step)*: real, database-backed donor directory/search/profiles/donation history, and batch-tracked inventory with low-stock/expiry alerts and admin batch management.
- **Step 4 — Blood requests, dashboard, and reports**: implement real request workflows (including stock deduction on fulfilment), a data-driven admin dashboard, and generated reports.
- **Step 5 — Testing, portability, and finalization**: testing, cleanup, and verifying the project runs on another machine for demonstration.

## Cloning the Repository

```bash
git clone <repository-url>
cd "Blood Bank Management System"
```

Then follow **Setup and Local Execution** above.

## Disclaimer

All donor names, contact details, blood group counts, inventory figures, and blood requests shown anywhere in this prototype are **fictional demonstration data**. They do not represent real people, real blood availability, or any real blood bank's inventory or requests.
