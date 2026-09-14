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
| Test ID | Test Scenario | Expected Outcome |
|---|---|---|
| `SEC-01` | SQL Injection in search query (`' OR 1=1 --`) | Safe parameterized query, 0 or exact literal match |
| `SEC-02` | XSS payload in invitee name (`<script>alert(1)</script>`) | Rendered as text via `textContent`, no script execution |
| `SEC-03` | CSRF token missing on POST request | 403 Forbidden |
| `SEC-04` | Upload file exceeding size limit (>10MB) | 413 Payload Too Large / 400 Bad Request |

---

## 3. Execution Methodology
1. **Automated Unit & Integration Tests**: Executed via `python manage.py test`.
2. **Browser Subagent Verification**: Automated end-to-end browser walkthrough inspecting visual elements, network requests, modals, and responsive layout.
