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

## Current Implementation Status: Step 2 — Backend, Database & Authentication

Step 1 delivered a frontend prototype with fictional, client-side-only data. **Step 2 adds a real Flask backend, a persistent SQLite database, and working authentication** (registration, login, logout, server-side sessions, and role-based authorization), and connects the existing login/registration pages to it.

What's real now:
- Registering a donor account creates real `users` and `donors` rows in a SQLite database on disk.
- Logging in verifies a hashed password against the database and starts a real server-side session.
- The navbar, on every page, reflects your actual logged-in/out state and role (fetched from the backend, not guessed from local storage).
- The Admin page now requires a real authenticated administrator session; visiting it while logged out or logged in as a regular user redirects you to Log In.

What's still fictional / not yet wired up (planned for Steps 3–4):
- The donor directory, inventory, blood-request submission, admin dashboard widgets, and reports still display the Step 1 **mock data** (`assets/js/mock-data.js`), not live database records.
- There is no donor-approval workflow, inventory editing, or request-processing yet — only the database tables and relationships that Steps 3–4 will build on.

## Architecture

```
Browser (Step 1 HTML/CSS/JS, served by Flask)
        │  fetch() JSON requests, same-origin
        ▼
Flask app (backend/app.py)
  ├─ backend/auth.py    — /api/auth/* : register, login, logout, me, CSRF token
  ├─ backend/admin.py   — /api/admin/* : admin-only endpoints (role enforced server-side)
  ├─ backend/models.py  — parameterized SQL data access (no ORM)
  └─ backend/database.py — SQLite connection + schema (instance/bloodbank.db)
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
│   ├── donors.html             # Searchable donor directory (still mock data)
│   ├── inventory.html          # Blood inventory overview (still mock data)
│   ├── requests.html           # Submit / view blood requests (still mock data)
│   ├── admin.html               # Administrator dashboard (now requires real admin login)
│   └── reports.html            # Summary reports (print-friendly, still mock data)
├── assets/
│   ├── css/
│   │   └── style.css           # Shared custom styles
│   ├── js/
│   │   ├── main.js             # Shared interactive behaviour (nav, validation, password toggles)
│   │   ├── mock-data.js        # Fictional demo data still used by donors/inventory/requests/reports
│   │   └── auth.js             # NEW — talks to the backend: session-aware nav, login/register forms
│   └── images/
│
├── backend/                   # NEW — Flask application
│   ├── app.py                   # create_app(), serves the frontend + registers API blueprints
│   ├── config.py                 # Config / TestConfig, loaded from environment variables
│   ├── database.py               # SQLite connection handling + schema (CREATE TABLE IF NOT EXISTS)
│   ├── models.py                  # Parameterized SQL data-access functions
│   ├── auth.py                    # /api/auth/* routes + login_required / admin_required decorators
│   └── admin.py                   # /api/admin/* routes (admin-only)
│
├── database/                  # NEW — one-off scripts, not imported by the app at request time
│   ├── init_db.py               # Creates the database/tables if missing (idempotent)
│   ├── seed_data.py              # Inserts fictional donors/inventory/requests/donations (idempotent)
│   └── create_admin.py           # Provisions a local admin account from .env (not a public API)
│
├── tests/                      # NEW — automated backend tests (pytest)
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_database.py
│
├── instance/                   # NEW, gitignored — bloodbank.db + session files live here
├── .venv/                      # NEW, gitignored — Python virtual environment
├── requirements.txt            # NEW
├── .env.example                # NEW — copy to .env and fill in real values
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

### 5. Initialize the database

```bash
python database/init_db.py
```

This creates `instance/bloodbank.db` and all tables. Safe to re-run any time — it never deletes existing data.

### 6. Load demonstration data (optional but recommended)

```bash
python database/seed_data.py
```

Inserts fictional donors, inventory batches, blood requests, and donation records. Safe to re-run — it skips any table that already has rows, so it never duplicates data.

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

## Authentication Endpoints

All endpoints return JSON. State-changing requests (`POST`) require the `X-CSRFToken` header, obtained from `GET /api/auth/csrf-token`; `assets/js/auth.js` handles this automatically for the frontend.

| Method & Path | Purpose | Auth required |
|---|---|---|
| `GET /api/auth/csrf-token` | Issue a CSRF token for the current session | No |
| `POST /api/auth/register` | Create a new account (always role `user`) + donor profile | No |
| `POST /api/auth/login` | Verify credentials, start a server-side session | No |
| `POST /api/auth/logout` | End the current session | Yes |
| `GET /api/auth/me` | Return the current user's id, name, email, role | Yes |
| `GET /api/admin/summary` | Example admin-only endpoint (read-only counts) | Yes, role `admin` |

**Roles:** `user` (default for every public registration) and `admin` (provisioned only via `database/create_admin.py`, never self-assignable through the API — the register endpoint ignores any `role` field a client sends).

## Database Schema

SQLite, foreign keys enforced (`PRAGMA foreign_keys = ON` on every connection). Timestamps are ISO-8601 UTC strings (e.g. `2026-10-29T12:34:56.789Z`); plain dates (`last_donation_date`, `collected_date`, `expiry_date`, `donation_date`) are ISO-8601 dates (`2026-10-29`). Full definitions are in `backend/database.py`.

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | Login accounts: name, normalized email (unique), password hash, role, status | — |
| `donors` | Donor profiles: blood group, contact, city, status | `user_id` → `users.id` (nullable — a donor need not have a login account) |
| `blood_inventory` | Inventory batches per blood group, with expiry | — |
| `blood_requests` | Requests for blood: group, quantity, urgency, status | `user_id` → `users.id` (nullable) |
| `donations` | Individual donation records | `donor_id` → `donors.id` (`ON DELETE CASCADE`) |

This Step 2 schema is the **foundation** for Steps 3–4; no donor-approval, inventory-editing, or request-processing workflows are implemented against it yet.

## Running the Tests

```bash
pytest tests/ -v
```

Each test gets its own temporary SQLite database and session directory (via pytest's `tmp_path`), so running the suite never touches `instance/bloodbank.db` or your real data. As of this step, **24 tests pass**, covering registration validation, password hashing, duplicate-email rejection, login/logout, `/me`, role-based authorization (regular user vs. admin), schema creation, foreign-key enforcement, data persistence across connections, and seed-data idempotency.

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

## Current Limitations

- **Donor directory, inventory, requests, and reports still show Step 1's fictional mock data** — they are not yet wired to the real database. That is planned for Steps 3 and 4.
- **No donor-approval, inventory-editing, or request-processing workflows** exist yet, even though the underlying tables do.
- **No password-reset flow** ("Forgot password?" remains a disabled link).
- **No rate limiting** on login/registration attempts.
- The admin dashboard (`pages/admin.html`) now correctly requires an authenticated admin session to view, but its on-page widgets still render the Step 1 mock data, not live counts from the database (the real counts are available via `GET /api/admin/summary` and are covered by a test, but the dashboard UI isn't wired to call it yet — that's Step 3/4 scope).

## Planned Development Stages

- **Step 1 — Frontend & project foundation** *(done)*: complete HTML/CSS/JS prototype with mock data.
- **Step 2 — Flask backend, database, and authentication** *(this step)*: Flask API, SQLite database foundation, and real registration/login/logout/session/role-based access, connected to the existing login and registration pages.
- **Step 3 — Donor management and inventory**: connect the donor directory and inventory pages to real CRUD operations against the database.
- **Step 4 — Blood requests, dashboard, and reports**: implement real request workflows, a data-driven admin dashboard, and generated reports.
- **Step 5 — Testing, portability, and finalization**: testing, cleanup, and verifying the project runs on another machine for demonstration.

## Cloning the Repository

```bash
git clone <repository-url>
cd "Blood Bank Management System"
```

Then follow **Setup and Local Execution** above.

## Disclaimer

All donor names, contact details, blood group counts, inventory figures, and blood requests shown anywhere in this prototype are **fictional demonstration data**. They do not represent real people, real blood availability, or any real blood bank's inventory or requests.
