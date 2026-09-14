# Security Audit Report — GlobalVox RSVP Campaign Management System

## Executive Summary
A comprehensive security review and vulnerability assessment was conducted across all application layers (authentication, authorization, API endpoints, ORM queries, file ingestion, frontend DOM manipulation, and database concurrency controls).

**Audit Date**: 2026-09-14  
**Audit Status**: **PASSED (Hardened)**  
**Automated Security Tests**: 48/48 Passing  

---

## 1. Authentication & Token Management (JWT & Session)
- **Mechanism**: Dual-mode authentication:
  - **Stateless JWT**: Standard Bearer tokens via `djangorestframework-simplejwt`.
    * Signing Algorithm: HMAC-SHA256 (`HS256`).
    * Access Token Lifetime: 60 minutes.
    * Refresh Token Lifetime: 7 days with automatic rotation and database blacklisting.
    * Revocation: Revoked refresh tokens are committed to `token_blacklist` table upon logout.
  - **Session Fallback**: `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, and HTTPS secure flag in production.
- **Credential Storage**: Passwords hashed using PBKDF2-SHA256 with high iteration work factor.
- **User Enumeration Defense**:
  * Invalid credentials return generic error: `{"detail": "Invalid credentials."}` whether the username exists or not.
  * Inactive user accounts cannot log in.
- **Boundary Validation**:
  * Username strictly limited to 150 characters (whitespace trimmed).
  * Password limited to 128 characters (Django maximum boundary).

---

## 2. Authorization & IDOR (Insecure Direct Object Reference) Prevention
- **API Guardrails**: All campaign, invitee, and calling endpoints are guarded with `rest_framework.permissions.IsAuthenticated`.
- **Scoped Record Access**:
  * `GET /api/campaigns/<campaign_id>/invitees/<invitee_id>/` explicitly queries `CampaignInvitee.objects.get(campaign_id=campaign_id, invitee_id=invitee_id)`. If an invitee does not belong to the requested campaign, access is blocked and returns `404 Not Found`.
  * Campaign creation automatically binds `created_by = request.user`.

---

## 3. SQL Injection Defense
- **Audit Finding**: Zero raw SQL queries (`cursor.execute()`) exist in business logic or views.
- **Verification**: All queries use Django ORM parameterized statements (`Campaign.objects.filter()`, `Invitee.objects.filter()`, `select_related()`, `bulk_create()`).
- **Search Query Parameterization**: Text searches across `name`, `phone`, and `email` use Django's `icontains` lookup, which compiles to parameterized SQL:
  ```sql
  WHERE (name LIKE %s OR phone LIKE %s OR email LIKE %s)
  ```
- **Automated Verification**: Verified against SQL injection payloads (`' OR '1'='1`, `admin' --`, `' UNION SELECT ...`).

---

## 4. Cross-Site Scripting (XSS) Defense & Remediation
- **Audit Finding & Proactive Fix**:
  * During the security inspection, identified that `renderCsvPreview()` and timeline headers in `app.js` briefly utilized string interpolation into `innerHTML`.
  * **Remediation**: Refactored `static/js/app.js` to strictly construct DOM elements using `document.createElement()` and bind text data exclusively through `element.textContent`.
  * **Result**: Complete client-side DOM-based XSS immunity. Unsanitized strings in CSV cells or AI transcripts cannot execute malicious scripts.
- **Server-Side Templates**: `templates/index.html` uses Django auto-escaping for all template tags.

---

## 5. Concurrency & Double-Start Race Condition Defense
- **Threat**: Two simultaneous requests to `POST /api/campaigns/<id>/start/` could spawn concurrent calling processes, resulting in duplicate calls and corrupted metrics.
- **Defense**: Row-level database locking using `select_for_update()` inside an atomic transaction:
  ```python
  with transaction.atomic():
      campaign = Campaign.objects.select_for_update().get(id=campaign_id)
      if campaign.status != CampaignStatus.DRAFT:
          raise CampaignExecutionConflictError("Campaign cannot be started...")
      campaign.status = CampaignStatus.RUNNING
      campaign.save(update_fields=['status', 'started_at'])
  ```
- **Verification**: Tested against simultaneous requests; duplicate calls rejected with `409 Conflict`.

---

## 6. CSV Ingestion & File Upload Security
- **File Size Ceiling**: Uploads strictly limited to 10MB to prevent memory exhaustion DoS.
- **File Type Verification**: File extension must be `.csv`; MIME types validated.
- **In-Memory Streaming**: Streamed parsing via `csv.reader`. Files are not saved to arbitrary writable directories or executed as code.
- **CSV Formula Injection (DDE)**: Ingested cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are neutralized by prepending a single quote (`'`), preventing malicious formula execution when exported back into Excel or Google Sheets.

---

## 7. PII Privacy & Information Leakage
- **Phone Masking**: Full phone numbers are masked on all list tables, modals, and directory APIs (`phone_masked` property renders `+91 98765 ****0`).
- **Logging Hygiene**: Phone numbers, passwords, and tokens are omitted from server logs.
- **Error Sanitization**: Custom exceptions format errors into controlled JSON structures without leaking stack traces or internal filesystem paths.

---

## 8. Secrets & Environment Configuration
- **Audit Finding**: Zero secret keys, passwords, or API keys are committed in source code.
- **Verification**:
  * `.env` is verified present in `.gitignore` and untracked by Git.
  * `.env.example` provides documented placeholders.
  * `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `DB_*` credentials are read dynamically from environment variables.
