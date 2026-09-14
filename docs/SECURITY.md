# Security Architecture & Policies — GlobalVox RSVP System

## 1. Threat Model & Principles
The RSVP Campaign Management system processes sensitive contact data (names, phone numbers, emails) and controls automated voice calling campaigns. The application must prevent unauthorized access, data leaks, campaign state race conditions, and injection vulnerabilities.

---

## 2. Authentication & Session Security
- **Mechanism**: Django Session Authentication with secure HTTP-only cookies and/or Token Authentication for API calls.
- **Credential Storage**: Passwords hashed using PBKDF2 with SHA256 (Django default with high work factor).
- **Session Protection**:
  - `SESSION_COOKIE_HTTPONLY = True` (Prevents client-side JS access to session cookie).
  - `SESSION_COOKIE_SAMESITE = 'Lax'` (Mitigates cross-site request forgery).
  - `SESSION_COOKIE_SECURE = True` in production (enforces HTTPS transmission).
- **Brute Force Defense**: Login view throttles repeated failed attempts per IP address.

---

## 3. Authorization & IDOR (Insecure Direct Object Reference) Prevention
- **Role Isolation**: All business management endpoints require `IsAuthenticated`.
- **Ownership Verification**: Campaign and invitee querysets are scoped to the authenticated organization or user. The server will never blindly trust a user-submitted `campaign_id` or `invitee_id` without verifying permissions.

---

## 4. Input Validation & Data Hygiene
- **Zero Frontend Trust**: Frontend validation serves solely as user feedback; all validations are strictly re-verified on the backend inside DRF serializers and service validators.
- **Phone Number Validation**: Stripped of non-numeric noise, validated against E.164 international standard or standard 10–15 digit phone patterns.
- **Email Validation**: Strict RFC-compliant validation via Django's `EmailValidator`.
- **Text & Name Fields**: Stripped of leading/trailing whitespace, length-limited, and sanitized.

---

## 5. File Upload & CSV Security
- **File Size Limit**: Uploads strictly limited to 10MB to prevent memory exhaustion and DoS.
- **File Type Verification**: File extension must be `.csv`, and MIME content-type must conform to `text/csv` or `text/plain`.
- **Parsing Safeguards**:
  - Streamed parsing using Python's standard `csv.reader` / `csv.DictReader`.
  - Malformed rows, null bytes, or excessive field counts are caught safely and isolated into the error report without crashing execution.
  - Uploaded files are processed in-memory or streamed and discarded; files are never executed or stored in publicly accessible directories.
- **CSV Formula Injection (CSV Injection / DDE)**: Fields beginning with `=`, `+`, `-`, or `@` are sanitized before export to prevent spreadsheet execution exploits.

---

## 6. Race Conditions & State Transition Concurrency
- **Campaign Double-Start Attack**:
  - If two browser requests hit `POST /api/campaigns/<id>/start/` simultaneously, an unchecked system could spawn duplicate concurrent calling processes.
  - **Mitigation**: Database-level atomic transition:
    ```python
    with transaction.atomic():
        campaign = Campaign.objects.select_for_update().get(id=campaign_id)
        if campaign.status != CampaignStatus.DRAFT:
            raise ConflictError("Campaign is already running or completed.")
        campaign.status = CampaignStatus.RUNNING
        campaign.started_at = timezone.now()
        campaign.save(update_fields=['status', 'started_at'])
    ```
- **Idempotent Results**: Unique constraints on `(campaign_invitee, attempt_number)` prevent duplicate call records.

---

## 7. Injection Defenses
- **SQL Injection**: Exclusively handled via Django ORM query parameters. Raw SQL statements are prohibited.
- **Cross-Site Scripting (XSS)**:
  - Frontend renders dynamic text via `element.textContent = ...` or DOM node creation.
  - Never uses `innerHTML` with unsanitized user inputs.
  - Output encoding applied to all data in HTML templates.
- **Cross-Site Request Forgery (CSRF)**:
  - Django CSRF middleware enabled.
  - State-changing HTTP verbs (`POST`, `PUT`, `PATCH`, `DELETE`) require the valid `X-CSRFToken` header.

---

## 8. Secrets & Configuration Management
- **Zero Secrets in Code**: No passwords, API keys, database credentials, or secret keys committed to Git.
- **Environment Driven**: `python-dotenv` loads environment variables from `.env`.
- **Template Provided**: `.env.example` contains placeholders and documentation.
- **Production Guardrails**:
  - `DEBUG = False` in production.
  - Explicit `ALLOWED_HOSTS` domain list.

---

## 9. Error Handling & Information Leakage
- **No Stack Traces**: DRF custom exception handlers format all unhandled exceptions into sanitized JSON responses:
  ```json
  {"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred. Please try again later."}}
  ```
- Detailed traceback logs are recorded strictly on the server stderr/logging handlers, never sent to client browsers.

---

## 10. Privacy & PII Protection
- **Phone Masking**: Phone numbers presented on dashboard UI and list tables are masked (e.g. `+91 98765 ****0`), protecting invitee privacy from casual observation while retaining operational context for the business user.
- **Logging Hygiene**: Phone numbers, passwords, and tokens are omitted from server log outputs.
