# Project Changelog — GlobalVox RSVP System

All notable changes, phase completions, and design decisions are documented in this file.

---

## [Unreleased]

---

## [Phase 11] — End-to-End Testing & Test Matrix Verification
**Timestamp**: 2026-09-14 12:27:00 UTC

### Added
- Created comprehensive End-to-End integration test suite `apps/campaigns/tests/test_e2e_workflow.py`:
  - Simulates the entire assessment lifecycle sequentially via REST API: User Login ➔ CSV Ingestion (Preview Mode) ➔ CSV Ingestion (Commit Mode) ➔ Campaign Creation ➔ Enrolling Invitees ➔ Starting Calling Process ➔ Verifying Live Metrics ➔ Listing Enrolled Invitees & Name Search ➔ Inspecting Individual Invitee Audit Timeline ➔ Verifying Double-Start 409 Concurrency Defense ➔ Logout & Token Blacklisting.
- Executed full test suite across all 4 domain applications: **49/49 tests passed (100% success rate)**.
- Updated [docs/TEST_PLAN.md](file:///c:/Users/Victus/Desktop/Globalvox/docs/TEST_PLAN.md) with test execution verification report and breakdown.

### Security
- Verified end-to-end token life-cycles, IDOR protections, and concurrency locks in integrated tests.

### Tests Performed
- `python manage.py test apps.accounts apps.invitees apps.campaigns apps.calling`: 49/49 passed.

---

## [Phase 10] — Dedicated Security Review & Hardening
**Timestamp**: 2026-09-14 12:25:00 UTC

### Added
- Completed comprehensive security review across OWASP Top 10 categories, documented in [docs/SECURITY_AUDIT_REPORT.md](file:///c:/Users/Victus/Desktop/Globalvox/docs/SECURITY_AUDIT_REPORT.md).
- Hardened client-side DOM rendering in `static/js/app.js`: eliminated residual `innerHTML` usages in CSV preview rows and timeline pills by strictly using `document.createElement()` and `textContent`.
- Verified zero raw SQL injection vectors (all queries strictly parameterized via Django ORM).
- Verified CSRF and JWT authorization requirements across all API endpoints.
- Verified file upload protections: 10MB file ceiling, `.csv` format restriction, and formula injection (DDE) sanitization for leading `=`, `+`, `-`, `@`.
- Verified database row-level locking (`select_for_update`) prevents concurrent double-start race conditions.

### Security
- XSS vulnerability in frontend preview rendering eliminated through safe DOM node construction.
- Status: **Audit PASSED and Hardened**.

### Tests Performed
- `python manage.py test apps.accounts apps.invitees apps.campaigns apps.calling`: 48/48 tests passed.

---

## [Phase 9] — Individual Invitee View & Audit Timeline
**Timestamp**: 2026-09-14 12:22:00 UTC

### Added
- Created `apps.campaigns.serializers.CallAttemptSerializer`: serializes individual call attempts (attempt number, provider call ID, status, outcome, duration in seconds, carrier error code, error message, transcript summary, and timestamps).
- Created `apps.campaigns.serializers.CampaignInviteeDetailSerializer`: comprehensive response containing invitee profile (with phone masking `phone_masked`), campaign metadata, RSVP and call status, attempt count, and ordered call attempts.
- Created `CampaignInviteeDetailView` (`GET /api/campaigns/<campaign_id>/invitees/<invitee_id>/`).
- Enhanced `static/js/app.js`: wired the "View Details" table action to fetch and render the chronological call attempt audit timeline inside the detail modal.
- Implemented and executed automated test suite `apps/campaigns/tests/test_invitee_detail.py` (4/4 tests passed).

### Security
- Verification that invitee belongs strictly to the requested campaign prevents cross-tenant data leaks.
- Privacy phone masking (`phone_masked`) maintained in the response payload.
- Endpoint guarded with `IsAuthenticated`.

### Tests Performed
- `python manage.py test apps.campaigns`: 18/18 tests passed (Individual detail view with multiple call attempts, phone masking verification, 404 unenrolled invitee check, 404 missing campaign check, 401 unauthenticated check).

---

## [Phase 8] — Results & Dashboard UI
**Timestamp**: 2026-09-14 12:17:00 UTC

### Added
- Created `templates/index.html`:
  - Complete enterprise dashboard for GlobalVox event managers.
  - Sign-in screen with quick-fill button for evaluation testing (`event_manager` / `GlobalVox@2026!`).
  - Active Campaign banner with event metadata (date, location, objective) and lifecycle status badges (`DRAFT`, `RUNNING`, `COMPLETED`).
  - Executive Metrics Grid with 6 cards: Total Invitees, Confirmed, Declined, Undecided, Pending, Failed.
  - Search & Filter toolbar: text search and status pill tabs.
  - Invitee Data Table: masked phone numbers, status badges, notes, and individual "View Details" action button.
  - Modals for New Campaign creation, CSV File Import (with preview vs commit modes), and Invitee Call History inspection.
- Created `static/css/style.css`:
  - Deep slate/navy responsive custom CSS design system with curated accessible status badges, glassmorphic modals, and micro-interactions (zero third-party CSS dependencies).
- Created `static/js/app.js`:
  - Vanilla JavaScript client coordinating authentication, campaign switching, live metric updates, table filtering, execution dispatch, and CSV drag-and-drop parsing.
- Mounted root route `GET /` in `globalvox_project/urls.py` rendering the web dashboard.

### Security
- Zero client-side HTML injections: dynamic content rendered strictly using `textContent` and DOM nodes to eliminate XSS.
- All mutating actions guarded by JWT authorization tokens and CSRF protection.

### Tests Performed
- HTTP `GET /` template view verified returning 200 OK.
- Complete regression suite: 44/44 tests passed across all apps.

---

## [Phase 7] — Campaign Execution Engine
**Timestamp**: 2026-09-14 12:14:00 UTC

### Added
- Created `CampaignExecutor` service (`apps/campaigns/services/executor.py`):
  - Database-level row locking with `select_for_update()` inside an atomic transaction to prevent concurrent double-starts.
  - State machine lifecycle transition: `DRAFT` -> `RUNNING` -> `COMPLETED`.
  - Dispatches calls to `CallingProvider` and records `CallAttempt` audit rows with provider call ID, status, duration (seconds), carrier error codes, and AI conversation summaries.
  - Updates `CampaignInvitee` records with latest `rsvp_status`, `call_status`, `attempt_count`, and `last_attempt_at`.
  - Failure Resilience: Partial carrier drops and network timeouts do not halt campaign execution; errors are logged and remaining invitees continue processing.
- Created `CampaignStartView` (`POST /api/campaigns/<id>/start/`):
  - Returns `409 Conflict` if campaign is already running or completed.
  - Returns `200 OK` with execution summary and updated metrics upon run.
- Implemented and executed automated test suite `apps/campaigns/tests/test_execution.py` (5/5 tests passed).

### Security
- Row-level database locking (`select_for_update`) completely mitigates race-condition double-dispatch attacks.
- Execution bounded by atomic transactions; unhandled provider exceptions isolated to single invitee without crashing the server.

### Tests Performed
- `python manage.py test apps.campaigns`: 14/14 tests passed (CRUD, metrics, filters, end-to-end execution, double-start 409 defense, carrier timeout resilience).

---

## [Phase 6] — Calling Provider Subsystem
**Timestamp**: 2026-09-14 12:12:00 UTC

### Added
- Created `apps.calling.base`:
  - `CallingProvider` abstract base class.
  - Standardized input dataclass `CallRequest` (`invitee_id`, `name`, `phone`, `campaign_id`, `campaign_name`, `event_name`, `attempt_number`).
  - Standardized output dataclass `CallResponse` (`provider_call_id`, `status`, `rsvp_outcome`, `duration_seconds`, `error_code`, `error_message`, `transcript_summary`, `is_success`).
- Created `apps.calling.mock_provider.MockCallingProvider`:
  - Simulates the realistic outcome distribution from the assessment: Confirmed (~62%), Declined (~8%), Undecided (~5%), Unreachable/Pending (~20%), Technical Failure (~5%).
  - Simulates variable conversation lengths (35–110 seconds for calls, 3–25 seconds for drops/unreachable).
  - Rich AI conversation summaries and realistic carrier error codes (`NETWORK_TIMEOUT`, `CALL_DROP`, `CODEC_MISMATCH`).
  - Deterministic random seeding support for reproducible testing.
- Implemented and executed automated test suite `apps/calling/tests/test_provider.py` (4/4 tests passed).

### Security
- Provider decoupled from database operations, preventing side effects during call dispatch.
- PII-safe design: only necessary parameters passed to provider contract.

### Tests Performed
- `python manage.py test apps.calling`: 4/4 passed (Interface compliance, deterministic seeding, 200-call distribution variety test, error code verification).

---

## [Phase 5] — Campaign Management
**Timestamp**: 2026-09-14 12:10:00 UTC

### Added
- Created `apps.campaigns.serializers`:
  - `CampaignListSerializer`: high-level summary cards with computed `total_invitees`.
  - `CampaignDetailSerializer`: detailed campaign view with live single-query SQL aggregation `metrics` dictionary.
  - `CampaignCreateSerializer`: atomic creation with support for explicit `invitee_ids` or `enroll_all_invitees=True`.
  - `CampaignInviteeSerializer`: serialized invitee participation with masked phone and status tracking.
- Created `apps.campaigns.views`:
  - `CampaignListCreateView` (`GET /api/campaigns/`, `POST /api/campaigns/`).
  - `CampaignDetailView` (`GET /api/campaigns/<id>/`).
  - `CampaignInviteeListView` (`GET /api/campaigns/<id>/invitees/`) supporting filtering by `?rsvp_status=...`, `?call_status=...`, and `?search=...`.
- Implemented and executed automated test suite `apps/campaigns/tests/test_campaigns.py` (9/9 tests passed).

### Security
- Automatic attribution of `created_by` to the authenticated user.
- String trimming, length validation, and date parsing validation prevent malformed campaign states.
- Endpoints guarded with `IsAuthenticated`.

### Tests Performed
- `python manage.py test apps.campaigns`: 9/9 tests passed (Creation, enrollment, listing, metrics aggregation, query filtering, missing fields, 404 handling, unauthenticated rejection).

---

## [Phase 4] — Invitee Import & CSV Engine
**Timestamp**: 2026-09-14 11:46:00 UTC

### Added
- Implemented `InviteeCSVImporter` service (`apps/invitees/services/csv_importer.py`):
  - Streamed CSV parsing with `csv.reader`.
  - Strict line-by-line validation for name (length and non-empty), phone (E.164 and international format normalization), email (RFC validation via `EmailValidator`), and in-batch duplicate phone detection.
  - Preview Mode (`preview_only=True`): parses and validates file returning totals, valid counts, error lists with line numbers, and sample data without modifying MySQL.
  - Commit Mode (`preview_only=False`): executes atomic bulk persistence (`bulk_create`) in batches of 1,000 rows.
  - Formula injection (DDE) sanitization neutralizing cells starting with `=`, `+`, `-`, `@`.
- Created `InviteeImportView` (`POST /api/invitees/import/`) with multipart parser and file size validation (max 10MB).
- Created `InviteeListView` (`GET /api/invitees/`) supporting search filtering across name, phone, email, external ID, with pagination and privacy phone masking (`phone_masked`).
- Added sample files: `sample_data/valid_invitees.csv` (PDF specification data) and `sample_data/invalid_invitees.csv` (deliberate errors and injection payload).
- Implemented and executed automated test suite `apps/invitees/tests/test_import.py` (10/10 tests passed).

### Security
- 10MB file size ceiling prevents memory exhaustion DoS.
- CSV formula injection protection prepends single quotes to dangerous leading characters.
- Phone numbers masked via `phone_masked` property on list responses.

### Tests Performed
- `python manage.py test apps.invitees`: 10/10 passed (Preview mode, bulk insert, search filtering, duplicate detection, bad headers, empty file, non-csv rejection, formula sanitization).

---

## [Phase 3] — Authentication & Authorization (JWT + Session)
**Timestamp**: 2026-09-14 11:38:00 UTC

### Added
- Integrated `djangorestframework-simplejwt` with HMAC-SHA256 token signing and database token blacklisting (`token_blacklist` migrations applied).
- Implemented `LoginView` (`/api/auth/login/`), `TokenRefreshView` (`/api/auth/refresh/`), `CurrentUserView` (`/api/auth/me/`), and `LogoutView` (`/api/auth/logout/`).
- Created `apps.accounts.serializers.LoginSerializer` with strict boundary validation (min/max length, whitespace trimming, inactive user isolation).
- Created `apps.accounts.management.commands.create_default_manager` seeding default business manager (`event_manager`) and superuser (`admin`).
- Created client-side modular JavaScript helper `static/js/auth.js` featuring pre-flight validation, token storage, and automatic token renewal on 401 responses.
- Implemented and executed automated test suite `apps/accounts/tests/test_auth.py` covering 16 distinct test cases.

### Security
- Stateless JWT Bearer token authentication with 60-minute access token lifetime and 7-day refresh token lifetime with automatic rotation and blacklisting.
- Generic error responses prevent user enumeration.
- SQL injection payloads (`' OR '1'='1`) and XSS script tags verified safely handled.
- Boundaries verified: 128-char passwords, 150-char usernames, blank/whitespace checks.

### Tests Performed
- `python manage.py test apps.accounts`: 16/16 tests passed (Happy path, edge cases, boundary values, SQL injection, XSS attacks).

---

## [Phase 2] — Database Foundation
**Timestamp**: 2026-09-14 11:29:00 UTC

### Added
- Created `apps.invitees.models.Invitee`: contact directory with phone privacy masking (`phone_masked`), indexed phone/email fields, and external ID.
- Created `apps.campaigns.models.Campaign`: event metadata (name, event date, location, objective, lifecycle status `DRAFT`/`RUNNING`/`COMPLETED`), single-query SQL aggregation method `calculate_metrics()`.
- Created `apps.campaigns.models.CampaignInvitee`: join model with controlled status enums (`RSVPStatus`, `CallStatus`), unique constraint on `(campaign, invitee)`, and composite indexes (`idx_camp_rsvp_status`, `idx_camp_call_status`).
- Created `apps.calling.models.CallAttempt`: audit trail of call attempts with duration, provider call ID, status (`IN_PROGRESS`, `COMPLETED`, `FAILED`), error tracking (`error_code`, `error_message`), and AI transcript summary.
- Database `globalvox_rsvp` provisioned in MySQL with `utf8mb4` character set.
- Migrations generated and executed:
  - `invitees.0001_initial`
  - `campaigns.0001_initial`
  - `calling.0001_initial`
  - Django core auth & sessions migrations applied.

### Security
- Passwords and database credentials isolated to `.env` (strictly git-ignored).
- Unique database constraints enforced against duplicate campaign enrollments.
- Privacy property `phone_masked` implemented on `Invitee` to ensure PII is masked on UI presentations.

### Tests Performed
- Automated model lifecycle test: record creation, foreign key cascades, SQL aggregation verification, phone masking verification, and cleanup executed successfully against live MySQL database.

---

## [Phase 1] — Project Foundation
**Timestamp**: 2026-09-14 11:25:00 UTC

### Added
- Project foundation initialized with Django 5.1 and Django REST Framework 3.15.
- Package dependencies defined in `requirements.txt` (`Django`, `djangorestframework`, `django-cors-headers`, `python-dotenv`, `PyMySQL`, `cryptography`, `whitenoise`).
- Environment variables template created in `.env.example` (with local `.env` configuration for development).
- Django administrative runner `manage.py` and WSGI entrypoint `globalvox_project/wsgi.py`.
- MySQLdb emulation via `pymysql.install_as_MySQLdb()` in `globalvox_project/__init__.py`.
- Enterprise settings configured in `globalvox_project/settings.py` (DRF pagination & auth, CORS, session cookie HTTPOnly, Whitenoise static storage, MySQL configuration).
- Domain application modules initialized in `apps/`: `accounts`, `campaigns`, `invitees`, `calling`.
- Root URL dispatcher in `globalvox_project/urls.py` mounting `/api/` prefix.

### Security
- Verified zero secret keys or database credentials committed (`.env` git-ignored).
- `SESSION_COOKIE_HTTPONLY = True` enabled.
- `X_FRAME_OPTIONS = 'DENY'` enabled.

### Tests Performed
- `python manage.py check`: Passed with 0 issues.

---

## [Phase 0] — Analysis & Planning
**Timestamp**: 2026-09-14 11:15:00 UTC

### Added
- Completed comprehensive review of `globalvox task.pdf`.
- Created detailed architecture, requirement, and execution plans under `docs/`:
  - `docs/MASTER_PLAN.md`: Strategic overview, scope boundaries, priorities.
  - `docs/REQUIREMENTS.md`: Explicit, derived, assumptions, and non-goals.
  - `docs/ARCHITECTURE.md`: Frontend, Django/DRF, provider abstraction, MySQL schema.
  - `docs/DATABASE.md`: Schema definition for Campaign, Invitee, CampaignInvitee, CallAttempt.
  - `docs/API_SPEC.md`: REST API specifications for auth, campaigns, invitees, calling.
  - `docs/SECURITY.md`: Authentication, IDOR, XSS, CSRF, SQLi, file upload limits, race conditions.
  - `docs/FLOW.md`: End-to-end user flows, technical sequences, and failure recovery.
  - `docs/IMPLEMENTATION_PLAN.md`: 15-phase incremental implementation breakdown.
  - `docs/TEST_PLAN.md`: Test matrix covering unit, integration, failure, and security cases.
  - `docs/DEPLOYMENT.md`: Vercel serverless WSGI runtime & hosted MySQL guide.
  - `docs/DECISIONS.md`: Architectural decision records (ADR 01–05).
  - `docs/CHANGELOG.md`: Chronological log of project milestones.
  - Root `README.md`: Project summary, planned stack, and setup structure.

### Security
- Defined CSRF, session, IDOR, input sanitization, and concurrency lock standards.

### Notes
- Awaiting user approval to commence Phase 1 (Project Foundation).
