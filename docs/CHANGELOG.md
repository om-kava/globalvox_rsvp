# Project Changelog — GlobalVox RSVP System

All notable changes, phase completions, and design decisions are documented in this file.

---

## [Unreleased]

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
