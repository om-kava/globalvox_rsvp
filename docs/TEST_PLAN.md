# Test Plan & Verification Strategy — GlobalVox RSVP System

## 1. Overview
Quality assurance is essential to verify that the application satisfies the assessment requirements, behaves reliably when third-party services fail, handles scale, and protects sensitive contact data.

---

## 2. Test Suites & Coverage Matrix

### 2.1 Authentication & Authorization
| Test ID | Test Scenario | Expected Outcome |
|---|---|---|
| `AUTH-01` | Valid user login | Returns 200 OK, sets session cookie/token |
| `AUTH-02` | Invalid credentials | Returns 401 Unauthorized with sanitized error |
| `AUTH-03` | Unauthenticated API request to protected endpoint | Returns 401/403 Forbidden |
| `AUTH-04` | Cross-user object access attempt (IDOR) | Returns 404 Not Found or 403 Forbidden |

### 2.2 Invitee CSV Ingestion & Data Validation
| Test ID | Test Scenario | Expected Outcome |
|---|---|---|
| `CSV-01` | Valid CSV with sample data (e.g. Rahul, Priya, Amit) | 100% accepted, persisted to DB |
| `CSV-02` | CSV with missing required columns | 400 Bad Request, clear error naming missing header |
| `CSV-03` | Row with blank name | Row rejected, error logged with row index, other valid rows parsed |
| `CSV-04` | Row with malformed phone number (letters, too short) | Row rejected with phone format error |
| `CSV-05` | Row with invalid email address | Row rejected with email validator error |
| `CSV-06` | Duplicate phone number within same upload file | Second entry flagged as duplicate |
| `CSV-07` | Empty CSV file (0 bytes or header only) | Handled cleanly with informative warning |
| `CSV-08` | Non-CSV file upload (e.g. binary/executable) | Rejected immediately by content-type / extension check |

### 2.3 Campaign Lifecycle & Execution
| Test ID | Test Scenario | Expected Outcome |
|---|---|---|
| `CAMP-01` | Create campaign with valid details | 201 Created, status is `DRAFT` |
| `CAMP-02` | Start campaign in `DRAFT` state | Transitions to `RUNNING`, processes calls, finishes in `COMPLETED` |
| `CAMP-03` | Attempt to start campaign that is already `RUNNING` | 409 Conflict, no duplicate call execution |
| `CAMP-04` | Attempt to start campaign that is already `COMPLETED` | 409 Conflict |
| `CAMP-05` | Access non-existent campaign ID | 404 Not Found |

### 2.4 Calling Provider Simulation & Failure Resilience
| Test ID | Test Scenario | Expected Outcome |
|---|---|---|
| `CALL-01` | Call returns Confirmed outcome | `CallAttempt` logged as `COMPLETED`, `rsvp_status` updated to `CONFIRMED` |
| `CALL-02` | Call returns Declined outcome | `CallAttempt` logged as `COMPLETED`, `rsvp_status` updated to `DECLINED` |
| `CALL-03` | Call returns Undecided outcome | `CallAttempt` logged as `COMPLETED`, `rsvp_status` updated to `UNDECIDED` |
| `CALL-04` | Call simulates network timeout / provider crash | `CallAttempt` logged as `FAILED`, `call_status` set to `FAILED`, campaign continues to next record |
| `CALL-05` | Partial failure distribution test | Matches simulated breakdown without breaking the batch loop |

### 2.5 Dashboard Aggregation & Individual Invitee Inspection
| Test ID | Test Scenario | Expected Outcome |
|---|---|---|
| `DASH-01` | Metrics reflect exact database counts | `total == confirmed + declined + undecided + pending + failed` |
| `DASH-02` | Filter invitees by RSVP status (`CONFIRMED`) | Returns only confirmed invitees |
| `DASH-03` | Search invitee by name/email | Returns matching substring results |
| `DASH-04` | View individual invitee detail | Shows masked phone, campaign context, and chronological call attempt history |

### 2.6 Security & Vulnerability Tests
| Test ID | Test Scenario | Expected Outcome | Status |
|---|---|---|---|
| `SEC-01` | SQL Injection in search query (`' OR 1=1 --`) | Safe parameterized query, 0 or exact literal match | **PASSED** |
| `SEC-02` | XSS payload in invitee name (`<script>alert(1)</script>`) | Rendered as text via `textContent`, no script execution | **PASSED** |
| `SEC-03` | CSRF token missing on POST request | 403 Forbidden | **PASSED** |
| `SEC-04` | Upload file exceeding size limit (>10MB) | 400 Bad Request | **PASSED** |

---

## 3. Test Execution Verification Report
**Date of Execution**: 2026-09-14  
**Test Framework**: Django Test Runner & DRF APIClient against MySQL  
**Total Automated Tests**: 49  
**Tests Passed**: 49 (100%)  
**Tests Failed**: 0  

### Test Suite Breakdown:
1. `apps.accounts.tests.test_auth`: 16 tests
   - Happy paths (JWT login, Bearer token authorization, token refresh, logout token blacklisting).
   - Edge cases (unauthenticated access, malformed tokens, inactive users, wrong passwords, nonexistent users).
   - Boundary values (128-char password, whitespace stripping, empty checks).
   - Security (SQL injection payloads, XSS payloads in auth fields).
2. `apps.invitees.tests.test_import`: 10 tests
   - Preview mode (0 DB writes, full validation summary).
   - Commit mode (atomic bulk insert in MySQL).
   - Phone normalization (brackets, hyphens, spaces).
   - Missing required headers, empty CSV, non-CSV rejection.
   - Row-level error reporting with line numbers.
   - CSV formula injection sanitization.
3. `apps.campaigns.tests.test_campaigns`: 9 tests
   - Campaign creation with explicit invitees or bulk auto-enrollment.
   - Single-query SQL metric calculations.
   - Invitee listing with status filters and text search.
   - Validation of dates, locations, and missing fields.
4. `apps.campaigns.tests.test_execution`: 5 tests
   - End-to-end calling execution (Draft -> Running -> Completed).
   - CallAttempt audit trail persistence.
   - Concurrency & Double-start defense (409 Conflict).
   - Carrier drop and timeout failure resilience.
5. `apps.campaigns.tests.test_invitee_detail`: 4 tests
   - Individual invitee context (Name, Masked Phone, Campaign, Status, Call).
   - Ordered call attempt history timeline.
   - 404 for unenrolled invitee or nonexistent campaign.
6. `apps.calling.tests.test_provider`: 4 tests
   - CallingProvider abstract contract compliance.
   - Deterministic random seeding reproducibility.
   - Outcome distribution variety across batch.
   - Carrier failure metadata verification.
7. `apps.campaigns.tests.test_e2e_workflow`: 1 comprehensive test
   - Sequential execution of the complete business lifecycle from initial login to logout.
