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

## Current Implementation Status: Step 1 — Frontend Prototype

This step delivers a **complete, interactive frontend prototype** using fictional demonstration data. There is **no backend, no database, and no real authentication yet** — every form validates client-side only and nothing is persisted. All statistics, donors, inventory levels, and requests shown throughout the site are fictional sample data created for demonstration purposes.

## Technology Stack

| Layer | Technology |
|---|---|
| Structure | HTML5 (semantic markup) |
| Styling | CSS3, [Bootstrap 5.3](https://getbootstrap.com/) (via CDN) |
| Icons | [Bootstrap Icons 1.11](https://icons.getbootstrap.com/) (via CDN) |
| Behaviour | Vanilla JavaScript (ES6+), no framework or build step |
| Backend *(planned, Step 2)* | Python (Flask) |
| Database *(planned, Step 2–3, pending mentor approval)* | SQLite (original synopsis specifies MySQL) |
| Version control | Git & GitHub |

**External CDN dependency notice:** this prototype loads Bootstrap 5, Bootstrap Icons, and their JavaScript bundle from `cdn.jsdelivr.net`. An internet connection is required the first time each page loads (browsers cache the files afterward). No application code or user data is sent to these CDNs — they only serve static CSS/JS/font files.

## Project Directory Structure

```
Blood Bank Management System/
├── index.html                 # Landing page
├── pages/
│   ├── login.html              # Login form (frontend only)
│   ├── register.html           # Donor registration form
│   ├── donors.html             # Searchable donor directory
│   ├── inventory.html          # Blood inventory overview
│   ├── requests.html           # Submit / view blood requests
│   ├── admin.html               # Administrator dashboard (demo mode)
│   └── reports.html            # Summary reports (print-friendly)
├── assets/
│   ├── css/
│   │   └── style.css           # Shared custom styles
│   ├── js/
│   │   ├── main.js             # Shared interactive behaviour (nav, validation, password toggles)
│   │   └── mock-data.js        # Single source of fictional demo data used by every page
│   └── images/                 # (reserved for future image assets)
├── README.md
└── .gitignore
```

## Running the Frontend Locally

No build step, package manager, or server is required.

1. Clone or download this repository.
2. Open `index.html` directly in a web browser (double-click it, or right-click → Open with → your browser).
3. Navigate the site using the top navigation bar.

An internet connection is needed on first load so the browser can fetch Bootstrap/Bootstrap Icons from the CDN.

> **Optional:** if a page ever needs to be served over HTTP instead of opened as a local file (not required for this step), run a simple local server from the project root, e.g. `python -m http.server 8000`, then visit `http://localhost:8000`.

## Testing the Interactive Pages

- **Navigation:** click through Home → Find Donors → Inventory → Requests → Reports → Admin → Login/Register and confirm every link loads the correct page with no broken paths.
- **Donor directory (`pages/donors.html`):** type a name in the search box, choose a blood group and/or city filter, and confirm the table/result count updates live; click "Clear" to reset filters; search for a nonsense name to see the empty-results state.
- **Inventory (`pages/inventory.html`):** filter by blood group text and by stock status (Available/Low/Critical) and confirm the summary cards and table match.
- **Login (`pages/login.html`) / Register (`pages/register.html`):** submit with empty fields to see validation messages; use the eye icon to toggle password visibility; on Register, enter mismatched passwords to confirm the confirm-password error, then submit a fully valid form to see the demo success message.
- **Requests (`pages/requests.html`):** submit the form with missing fields to see validation, then a valid submission to see the demo confirmation; review the sample request-status table for status badges.
- **Admin dashboard (`pages/admin.html`):** switch between the Overview, Requests, and Inventory tabs in the sidebar and confirm each panel renders sample data correctly.
- **Reports (`pages/reports.html`):** review the donation/inventory/request summaries, then use "Print report" to preview the print-friendly layout.
- **Responsive layout:** resize the browser window (or use your browser's device toolbar) to confirm the navbar collapses into a hamburger menu and tables/cards reflow correctly on mobile widths.

## Current Limitations

- **No backend or persistence.** All data lives in `assets/js/mock-data.js` and resets on every page reload. Forms do not save, update, or delete anything.
- **No real authentication.** The login form and the "Admin" area are visual demonstrations only; they do not verify credentials or restrict access.
- **No real-time data.** Donor availability, inventory counts, and request statuses are fictional and static.
- **No backend validation.** Only client-side validation is implemented; a real system would also validate and sanitize data on the server.

## Planned Development Stages

- **Step 1 — Frontend & project foundation** *(this step)*: complete HTML/CSS/JS prototype with mock data.
- **Step 2 — Flask backend, database, and authentication**: introduce a Python Flask API, a database (SQLite, pending mentor approval), and real login/registration.
- **Step 3 — Donor management and inventory**: connect the donor directory and inventory pages to real CRUD operations against the database.
- **Step 4 — Blood requests, dashboard, and reports**: implement real request workflows, a data-driven admin dashboard, and generated reports.
- **Step 5 — Testing, portability, and finalization**: testing, cleanup, and verifying the project runs on another machine for demonstration.

## Cloning the Repository

Once this project has a GitHub remote configured:

```bash
git clone <repository-url>
cd "Blood Bank Management System"
```

Then open `index.html` in a browser as described above — no additional setup is required for this step.

## Disclaimer

All donor names, contact details, blood group counts, inventory figures, and blood requests shown anywhere in this prototype are **fictional demonstration data**. They do not represent real people, real blood availability, or any real blood bank's inventory or requests.
