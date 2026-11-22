# StockWise Soweto - BFB 321 Group 8

StockWise Soweto is a web-based inventory and replenishment tool for independent spaza shops. It brings stock, recent sales and supplier information into one place. It then recommends full-pack order quantities that fit the shop's cash and storage limits. The owner reviews every basket before an order is approved.

This implementation develops the Group 8 BFB 321 proposal into a complete Flask and MySQL application. It focuses on 20 non-refrigerated SKUs and does not introduce customer credit, refrigerated products or a new delivery service.

## Group members

| Name | Student number | GitHub username |
|---|---|---|
| Andrew Holdt | u23565081 | u23565081 |
| Austin Ferraz | u23627132 | u23627132-Ferraz |
| David de Villiers | u23570972 | 23570972 |
| David Plumb | u23526263 | u23526263-hash |

## Task allocation

This table records work that is visible in the repository history. It stays high-level where a member has not written their own detail. Shared product work from the initial upload is not split into invented personal task lists.

| Member | Focus recorded in the repository |
|---|---|
| Andrew Holdt (`u23565081`) | Initial project upload, and the Windows run documentation in `README.md` and `scripts/start.ps1` (Python installation and the Microsoft Store `python` alias). |
| Austin Ferraz | Added a “Record a movement” link to the dashboard when there are no stock entries. Added the year to movement dates to make older entries easier to identify. |
| David de Villiers (`23570972`) | Improved dashboard accessibility by hiding decorative icons from screen readers and clarified that the low-stock count includes stockouts (PR #2). |
| David Plumb (`u23526263-hash`) | Documentation and rubric readiness: GitHub usernames, this allocation, submission-checklist clarifications, and contribution notes. |

![Dashboard showing stock KPIs and recent movements](docs/screenshots/dashboard.png)

![Replenishment planner showing full-pack order suggestions](docs/screenshots/replenishment.png)

## What is included

- Responsive and accessible HTML/CSS/JavaScript frontend
- Flask application factory, blueprints and session-based login
- REST API with validation, pagination, filtering and consistent errors
- MySQL 8 schema with foreign keys, checks, indexes and audit timestamps
- Standalone Python replenishment model with documented formulas
- Five seeded model shops, two suppliers and 20 realistic demo SKUs
- 34 unit, integration and page tests using `pytest`
- Docker and local run scripts, environment template, migrations and rollback
- ER diagram, architecture diagram and OpenAPI contract
- Repeatable 28-day impact simulation and usability test pack

## Main user flows

1. **Record stock:** the owner records a sale, receipt, loss, return or count adjustment. The stock ledger prevents a negative balance. Sales also update daily demand history.
2. **Prepare an order:** the owner chooses a supplier and cash budget. The model calculates target stock, days of cover and full-pack quantities. Urgent items receive priority when cash or storage is limited.
3. **Approve and receive:** the owner creates a draft, approves it after constraint checks, then receives the delivery. Receipt movements update the stock ledger automatically.

These flows cover proposal features F1-F5 and objectives O1-O4.

## Setup and run from a clean machine

Install Git, Python 3.11 or newer, and MySQL Community Server 8 (including the
`mysql` command-line client). Start the MySQL service and add its `bin`
directory to PATH. Internet access is needed to install Python packages and
load Bootstrap from jsDelivr.

Development and production require a complete `mysql+pymysql://` DATABASE_URL.
Missing settings and SQLite URLs fail with setup instructions. In-memory SQLite
is reserved for TestingConfig in pytest only.

### 1. Clone and install (Windows PowerShell)

```powershell
git clone https://github.com/u23565081/BFB321_group_8.git
cd BFB321_group_8
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

If `python` opens the Microsoft Store, install Python from
<https://www.python.org/downloads/windows/>, select **Add python.exe to PATH**,
reopen PowerShell, and use `py -3` in place of `python`.

On Linux/macOS, use the same clone commands, then:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

### 2. Create the MySQL database and account

Connect as your MySQL administrator (enter its password when prompted):

```sh
mysql -u root -p
```

At the MySQL prompt, run these exact SQL statements on a fresh installation.
The example password is for local demonstration only; if you change it, use
the same password in .env.

```sql
CREATE DATABASE spaza_inventory CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'spaza_user'@'localhost' IDENTIFIED BY 'spaza_password';
GRANT ALL PRIVILEGES ON spaza_inventory.* TO 'spaza_user'@'localhost';
EXIT;
```

Import the schema from the project folder. PowerShell does not support input
redirection with `<`, so run it through cmd:

```powershell
cmd /c "mysql -h localhost -u spaza_user -p spaza_inventory < database\schema.sql"
```

On Linux/macOS:

```sh
mysql -h localhost -u spaza_user -p spaza_inventory < database/schema.sql
```

Enter `spaza_password` when prompted. If MySQL is on a different host, create
the account for the actual client host and adjust DATABASE_URL accordingly.

### 3. Configure the environment

Windows:

```powershell
Copy-Item .env.example .env
notepad .env
```

Linux/macOS:

```sh
cp .env.example .env
nano .env
```

Set the following values and save the file:

```dotenv
FLASK_ENV=development
FLASK_DEBUG=0
HOST=127.0.0.1
SECRET_KEY=replace-with-a-long-random-value
DATABASE_URL=mysql+pymysql://spaza_user:spaza_password@localhost:3306/spaza_inventory
LOG_LEVEL=INFO
```

Generate a secret with `python -c "import secrets; print(secrets.token_hex(32))"`
(use the venv Python on Windows). URL-encode special characters in database
passwords when putting them in DATABASE_URL. Existing process environment
variables take precedence over .env. Do not commit .env.

### 4. Seed and run

Windows:

```powershell
.\.venv\Scripts\python.exe database\seed.py
.\.venv\Scripts\python.exe run.py
```

Linux/macOS (with the virtual environment active):

```sh
python database/seed.py
python run.py
```

Seeding is idempotent. Open <http://127.0.0.1:5000> and sign in:

| Role | Email | Password |
|---|---|---|
| Shop owner | owner@demo.co.za | demo2026 |
| Administrator | admin@demo.co.za | admin2026 |

Press Ctrl+C to stop. Debugging is off by default; errors are logged and users
receive a friendly error page rather than a Werkzeug traceback. FLASK_DEBUG=1
is for local debugging only. HOST defaults to 127.0.0.1.

### Start scripts after database setup

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

```sh
sh scripts/start.sh
```

Both scripts copy .env.example to .env and stop if .env is missing. Edit it and
rerun. They require a MySQL URL, install dependencies, seed, then start the app.
They do not create the local MySQL account or import the SQL schema for you.

### MySQL run with Docker

Install and start Docker Desktop. Clone the repository, copy .env.example to
.env and set a secret as above, then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -MySQL
```

Or on Linux/macOS:

```sh
sh scripts/start.sh --mysql
```

Alternatively use `docker compose up --build` directly. Compose starts MySQL
8.4, imports the schema on its first empty volume, seeds the data and starts
Gunicorn. It supplies its own database connection to the web container; local
.env credentials do not replace those Compose defaults. The supplied Compose
credentials are for a local demo. Open <http://127.0.0.1:5000> and use the same
logins. Stop with `docker compose down`; restart with `docker compose up`.
The database volume persists. Port 3306 must be free when using Compose.

## Replenishment model

For each SKU:

```text
Target stock S = d × (L + R + b)
Inventory position IP = stock on hand + confirmed stock on order
Recommended q = pack size × ceil(max(0, S - IP) / pack size)
Days of cover = IP / d
```

Where `d` is estimated daily demand, `L` is supplier lead time, `R` is the review period, and `b` is the safety-stock allowance in days. The service estimates `d` from the latest 14 days. When demand is missing, the result is marked provisional. `models/replenishment.py` contains no Flask or database imports, so it can be tested on its own.

The allocator sorts products by days of cover, reserves the supplier delivery fee, and adds one full pack at a time while enough cash and storage remain. It never creates partial packs.

## REST API summary

All endpoints require a signed-in session. Full request and response details are in [the OpenAPI contract](docs/openapi.yaml).

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/v1/inventory` | Paginated and filtered stock balances |
| `POST` | `/api/v1/movements` | Record a stock movement |
| `GET` | `/api/v1/recommendations` | Calculate a constrained supplier basket |
| `GET` | `/api/v1/orders` | Paginated orders with status filtering |
| `POST` | `/api/v1/orders` | Create a full-pack draft order |
| `POST` | `/api/v1/orders/{id}/approve` | Recheck cash and storage, then approve |
| `POST` | `/api/v1/orders/{id}/receive` | Receive outstanding lines and update stock |

Validation errors use a consistent JSON structure:

```json
{
  "error": "validation_error",
  "message": "Quantity must be a whole number greater than zero.",
  "fields": ["quantity"]
}
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The tests cover:

- proposal Appendix A calculations and pack rounding;
- cash and storage allocation priority;
- login protection, pagination and filtering;
- stock movement validation and negative-stock prevention;
- draft → approve → receive integration flow;
- full-pack order validation; and
- rendering of all main pages.

The final run passed all 34 tests with 98% coverage across the application and calculation model. The desktop, tablet and phone browser checks are recorded in [the QA report](docs/qa_report.md).

Run the repeatable impact evaluation with:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_impact.py
```

The script writes JSON and CSV evidence to `docs/generated/`. Its results are model outputs, not results collected from live spaza shops.

## Design and submission evidence

- [Architecture diagram](docs/architecture.svg)
- [ER diagram](docs/erd.svg)
- [System design and data dictionary](docs/system_design.md)
- [OpenAPI contract](docs/openapi.yaml)
- [Impact and sustainability analysis](docs/impact_and_sustainability.md) (KPI figures are simulation outputs)
- [Contribution notes](docs/CONTRIBUTING_NOTES.md)
- [Test plan and results](docs/test_plan_and_results.md)
- [Website quality assurance report](docs/qa_report.md)
- [Usability evaluation](docs/usability_test_results.md)
- [Maintenance and handover guide](docs/maintenance_guide.md)

## Deployment and operations

Set `FLASK_ENV=production`, `FLASK_DEBUG=0`, a long random `SECRET_KEY`,
and a MySQL `DATABASE_URL` in the deployment environment. SQLite and a missing
database URL are rejected; production also rejects the development secret.
On a Linux host with dependencies installed:

```sh
python database/seed.py
gunicorn --bind 127.0.0.1:5000 --workers 2 --access-logfile - run:app
```

Put an HTTPS reverse proxy in front of Gunicorn. Containers need an explicit
`--bind 0.0.0.0:5000` (as in Compose); keep their published ports restricted
appropriately. HOST controls the Python development entry points, not Gunicorn.
Application logs rotate at 1 MB with three retained files. Never enable the
development debugger on a shared server.

Database migration and rollback:

```powershell
mysql -u root -p -e "SOURCE database/migrations/0001_initial.sql"
mysql -u root -p -e "SOURCE database/migrations/0001_rollback.sql"
```

Create a backup on Linux:

```sh
MYSQL_HOST=localhost MYSQL_USER=spaza_user MYSQL_DATABASE=spaza_inventory ./scripts/backup_mysql.sh
```

Restore after creating an empty database:

```sh
mysql -h localhost -u spaza_user -p spaza_inventory < backups/spaza_YYYYMMDD_HHMMSS.sql
```

Test migration and restore steps on a non-production database first. Keep daily backups for 14 days. The project rollback script removes all application tables and must only be used with a confirmed backup.

## Scalability and privacy

- `shop_id` separates records, while ownership checks stop one owner from reading another shop.
- Composite indexes support common inventory, demand and order lookups.
- API pagination prevents large stock lists from being loaded at once.
- The schema can add users and shops without changing replenishment calculations.
- Shop codes may replace public-facing names. No customer personal information is collected.
- A larger deployment should add CSRF protection for JSON writes, HTTPS, managed backups, rate limiting and stronger administration controls.

## References used from the proposal

- Cant & Associates (Pty) Ltd (2024), *Transforming the township retail market in South Africa: A sustainable growth and development model for spaza shops*.
- Coetzer, P. and Pascarel, N. (2014), ‘Last mile delivery in low income communities: The Sekulula Spaza Express experiment in South Africa’, *Field Actions Science Reports*, Special Issue 12.
- Deokaran, R. (2023), *The deployment of platform businesses in the township economy: A focus on spaza shops in Soweto*. University of the Witwatersrand.
- Eicker, T. and Cilliers, J.O. (2018), ‘Inventory decision-making by small Sowetan retailers’, *Journal of Transport and Supply Chain Management*, 12, a387.
- Hyndman, R.J. and Athanasopoulos, G. (2021), *Forecasting: Principles and Practice*, 3rd edition. OTexts.
