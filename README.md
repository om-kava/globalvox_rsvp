# GlobalVox RSVP — Voice AI Campaign Management System

An enterprise-grade, secure, and resilient web application designed for GlobalVox event management teams to organize, execute, and monitor automated AI voice calling RSVP campaigns.

Built for the **GlobalVox Software Engineering Assessment**.

---

## Table of Contents
- [Executive Overview](#executive-overview)
- [Key Features](#key-features)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Quick Start Guide (Local Setup)](#quick-start-guide-local-setup)
- [Evaluation Credentials](#evaluation-credentials)
- [Sample Test Datasets](#sample-test-datasets)
- [REST API Endpoints](#rest-api-endpoints)
- [Security & OWASP Compliance](#security--owasp-compliance)
- [Automated Test Matrix](#automated-test-matrix)
- [Deployment Guide (Vercel & Cloud MySQL)](#deployment-guide-vercel--cloud-mysql)
- [Assumptions & Limitations](#assumptions--limitations)
- [AI Usage Disclosure](#ai-usage-disclosure)
- [Documentation Index](#documentation-index)

---

## Executive Overview

GlobalVox RSVP replaces manual calling workflows with an automated, simulated AI voice calling platform. Event managers can:
1. Ingest contact lists via CSV with pre-commit validation.
2. Organize isolated campaigns with distinct metadata (Event Name, Date, Location, AI Objective).
3. Dispatch automated voice calling simulations with realistic conversational outcomes (Confirmed, Declined, Undecided, Unreachable/Pending, Failed).
4. Track real-time campaign outcomes via an executive dashboard.
5. Incrementally add new CSV batches to active campaigns without re-calling previously completed contacts.
6. Inspect granular call attempt audit timelines and transcripts for individual invitees with masked PII.

---

## Key Features

- **Strict Campaign Isolation**: Each campaign functions as an independent workspace. Contacts, metrics, and call logs never cross-contaminate unless explicitly chosen.
- **Incremental Multi-Batch Calling**: When new contacts are imported into an already executed campaign, the engine enables **"Call Pending Contacts (X)"** for only the newly added batch, preserving all prior call outcomes and history.
- **Pre-Commit CSV Validation Engine**: 10MB upload ceiling, phone number normalization, email validation, duplicate detection, and spreadsheet formula injection (DDE) sanitization with line-by-line error feedback.
- **Concurrency & Race-Condition Defense**: Database row-level locking (`select_for_update`) prevents concurrent double-starts (409 Conflict) across distributed requests.
- **Pluggable Telephony Provider Abstraction**: Clean `CallingProvider` abstract base class with a `MockCallingProvider` simulating realistic durations, transcripts, and voice distributions (~62% Confirmed, ~8% Declined, ~5% Undecided, ~20% Pending, ~5% Carrier Drops).
- **Failure Resilience**: Individual carrier errors or dropped calls log a `FAILED` audit attempt without crashing the campaign.
- **PII Privacy Protection**: Phone numbers are masked across the API and dashboard (`+919876 ****10`).
- **Interactive Evaluation "Reset / Re-run"**: Completed campaigns can be reset to `DRAFT` in one click to re-test the calling simulation repeatedly.

---

## Architecture & Tech Stack

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Client Dashboard                                │
│   Semantic HTML5 • Custom Responsive CSS3 • Vanilla ES6+ JavaScript    │
│            (Zero React / Vue / Tailwind Dependencies)                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / REST (JWT + CSRF)
┌───────────────────────────────────▼────────────────────────────────────┐
│                        Django 5.1 / DRF 3.15                           │
│  ┌───────────────────────┐ ┌──────────────────┐ ┌───────────────────┐  │
│  │   apps.accounts       │ │  apps.invitees   │ │  apps.campaigns   │  │
│  │   Auth / JWT Tokens   │ │  CSV Importer    │ │  Executor / State │  │
│  └───────────────────────┘ └──────────────────┘ └─────────┬─────────┘  │
│                                                           │            │
│                              ┌────────────────────────────▼─────────┐  │
│                              │            apps.calling              │  │
│                              │ CallingProvider ABC / Mock Provider  │  │
│                              └──────────────────────────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Django ORM / PyMySQL
┌───────────────────────────────────▼────────────────────────────────────┐
│                         MySQL Database                                 │
│    Relational Schema • Composite Indexes • Row-Level Atomic Locks      │
└────────────────────────────────────────────────────────────────────────┘
```

- **Frontend**: Vanilla HTML5, Vanilla CSS3 (curated slate/navy design tokens, responsive breakpoints, custom scrollbars, micro-animations), Vanilla ES6+ JavaScript.
- **Backend**: Python 3.13, Django 5.1.4, Django REST Framework 3.15.2, SimpleJWT.
- **Database**: MySQL 8.0 with relational foreign keys, composite status indexes, and unique constraints.
- **Static Assets**: WhiteNoise 6.8.2 compressed manifest storage.
- **Deployment Runtime**: Vercel serverless Python WSGI runtime (`api/index.py` + `vercel.json`).

---

## Quick Start Guide (Local Setup)

### 1. Prerequisites
- Python 3.11+ (Python 3.13 tested)
- MySQL Server 8.0+ running on `127.0.0.1:3306`
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/om-kava/globalvox_rsvp.git
cd globalvox_rsvp
```

### 3. Create & Activate Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env` and set your MySQL credentials:
```bash
# Windows PowerShell
copy .env.example .env

# Linux / macOS
cp .env.example .env
```
Edit `.env`:
```ini
DEBUG=True
DJANGO_SECRET_KEY=local-dev-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=globalvox_rsvp
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### 6. Create MySQL Database & Run Migrations
In your MySQL shell:
```sql
CREATE DATABASE IF NOT EXISTS globalvox_rsvp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
Run Django migrations:
```bash
python manage.py migrate
```

### 7. Seed Evaluation Accounts
```bash
python manage.py create_default_manager
```

### 8. Run Automated Tests
```bash
python manage.py test apps.accounts apps.invitees apps.campaigns apps.calling
```
*(Expected: 49/49 tests passed with 100% success rate).*

### 9. Start Development Server
```bash
python manage.py runserver
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

---

## Evaluation Credentials

| Role | Username | Password | Notes |
|---|---|---|---|
| **Event Manager** | `event_manager` | `GlobalVox@2026!` | Primary evaluator account *(Quick-fill button on UI)* |
| **Administrator** | `admin` | `Admin@GlobalVox2026!` | Django Superuser |

---

## Sample Test Datasets

All sample CSV files are located in the [sample_data/](sample_data/) directory:

- [sample_data/executive_board_5.csv](sample_data/executive_board_5.csv): 5-contact executive board for quick testing.
- [sample_data/tech_summit_vip.csv](sample_data/tech_summit_vip.csv): 15-contact VIP tech summit list.
- [sample_data/annual_conference_50.csv](sample_data/annual_conference_50.csv): 50-contact dataset for volume and distribution testing.
- [sample_data/valid_invitees.csv](sample_data/valid_invitees.csv): 10-contact standard valid dataset.
- [sample_data/edge_cases_and_formatting.csv](sample_data/edge_cases_and_formatting.csv): Edge cases with varied phone formats and formula injection sanitization.
- [sample_data/invalid_invitees.csv](sample_data/invalid_invitees.csv): Invalid data to test line-by-line validation errors.

---

## REST API Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `POST` | `/api/auth/token/` | Obtain JWT access & refresh tokens | Public |
| `POST` | `/api/auth/token/refresh/` | Refresh JWT access token | Public |
| `POST` | `/api/auth/token/blacklist/` | Invalidate/logout JWT refresh token | User |
| `GET` | `/api/auth/me/` | Current authenticated user profile | User |
| `GET` | `/api/campaigns/` | List all campaigns with aggregate metrics | User |
| `POST` | `/api/campaigns/` | Create a new isolated or populated campaign | User |
| `GET` | `/api/campaigns/<id>/` | Single campaign metadata and metrics | User |
| `POST` | `/api/campaigns/<id>/start/` | Start campaign / call pending invitees | User |
| `POST` | `/api/campaigns/<id>/reset/` | Reset campaign back to DRAFT state | User |
| `POST` | `/api/campaigns/<id>/enroll/` | Enroll contacts into campaign | User |
| `GET` | `/api/campaigns/<id>/invitees/` | List campaign invitees (filter & search) | User |
| `GET` | `/api/campaigns/<cid>/invitees/<iid>/` | Individual invitee call audit timeline | User |
| `POST` | `/api/invitees/import/` | CSV ingestion (preview vs. commit) | User |
| `GET` | `/api/invitees/` | Global directory of invitees | User |

---

## Security & OWASP Compliance

Documented comprehensively in [docs/SECURITY_AUDIT_REPORT.md](docs/SECURITY_AUDIT_REPORT.md):
- **SQL Injection**: 100% immune (all database queries use Django ORM parameterization).
- **Cross-Site Scripting (XSS)**: Client DOM rendering strictly uses `document.createElement()` and `textContent`.
- **Cross-Site Request Forgery (CSRF)**: CSRF tokens enforced on all mutating requests alongside JWT headers.
- **CSV Formula Injection (DDE)**: Cells beginning with `=`, `+`, `-`, `@` are automatically sanitized with leading single quotes.
- **PII Protection**: Customer phone numbers masked across all user-facing views.
- **Concurrency Protection**: Database row-level locks prevent race conditions on simultaneous starts.

---

## Automated Test Matrix

Run the test suite:
```bash
python manage.py test apps.accounts apps.invitees apps.campaigns apps.calling
```

- **`apps.accounts`** (16 tests): JWT login, token refresh, token blacklist, rate limiting, and permission boundaries.
- **`apps.invitees`** (10 tests): CSV parser validation, phone normalization, duplicate detection, formula sanitization, and preview mode.
- **`apps.campaigns`** (19 tests): Campaign CRUD, enrollment, metric aggregations, execution runner, concurrency double-start protection, individual invitee inspection, and 10-step end-to-end integration workflow.
- **`apps.calling`** (4 tests): `MockCallingProvider` distribution, duration calculation, and deterministic seed generation.

**Total**: **49 tests | 100% Pass Rate**.

---

## Deployment Guide (Vercel & Cloud MySQL)

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full production deployment instructions.

1. **Vercel Runtime**: Configured via [vercel.json](vercel.json) pointing to serverless WSGI entrypoint [api/index.py](api/index.py).
2. **Cloud MySQL**: Connect to any cloud-hosted MySQL instance (TiDB Cloud, Aiven, PlanetScale, or Railway) by setting environment variables in the Vercel dashboard:
   - `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`.
3. **Deploy Command**:
   ```bash
   vercel --prod
   ```

---

## Assumptions & Limitations

1. **Simulated Telephony**: In accordance with assessment instructions, no real PSTN/SIP phone calls are placed; telephony behavior is simulated by an internal `CallingProvider` abstraction.
2. **Execution Timing**: Calls execute in rapid mock batches (configurable via `MOCK_CALL_DELAY_MS`) to allow interactive evaluation without waiting hours.
3. **Background Worker Evolution**: For production scaling beyond 10,000 concurrent calls, Celery + Redis worker queues can be attached to the existing `CallingProvider` contract.

---

## AI Usage Disclosure

In compliance with the GlobalVox assessment guidelines:

### 1. AI Tools Used
- **Google DeepMind Antigravity Agentic IDE** powered by **Gemini 3.1 Pro**.

### 2. Productive Contributions
- Accelerated scaffolding of boilerplate Django REST Framework serializers and views.
- Generated comprehensive automated test matrices covering edge cases (DDE injection, phone normalization).
- Formulated modern responsive CSS design system tokens and micro-animations.

### 3. Verification, Modification, & Rejection Examples
- **Strict Campaign Isolation vs. Generic Auto-Enrollment**: An initial implementation auto-enrolled global contacts into new campaigns. Upon evaluation, this was **rejected and refactored** into a strict campaign isolation architecture where campaigns are completely independent workspaces.
- **Database Column Constraint Alignment**: When implementing the campaign reset view, an `IntegrityError` on `notes=None` was caught because the model was defined with `blank=True, default=""`. The AI code was **modified** to pass `notes=""` adhering to MySQL schema constraints.
- **XSS Defense Verification**: An automated audit spotted potential `innerHTML` usage in CSV preview rendering. This was **flagged and refactored** to safe DOM construction using `document.createElement()` and `textContent`.

---

## Documentation Index

- [docs/MASTER_PLAN.md](docs/MASTER_PLAN.md) — Architectural overview & technical plan
- [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) — Requirement specifications from assessment task
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — High-level architecture & domain boundaries
- [docs/DATABASE.md](docs/DATABASE.md) — Relational schema, indexes, and constraints
- [docs/API_SPEC.md](docs/API_SPEC.md) — Complete REST API contracts
- [docs/SECURITY.md](docs/SECURITY.md) — Security policies & defenses
- [docs/SECURITY_AUDIT_REPORT.md](docs/SECURITY_AUDIT_REPORT.md) — Dedicated OWASP Top 10 audit findings
- [docs/FLOW.md](docs/FLOW.md) — Lifecycle state machines and user journeys
- [docs/TEST_PLAN.md](docs/TEST_PLAN.md) — Quality assurance and test execution report
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Vercel & cloud MySQL deployment guide
- [docs/DECISIONS.md](docs/DECISIONS.md) — Architecture Decision Records (ADRs)
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — Complete phase-by-phase changelog
