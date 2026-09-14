# API Specification — GlobalVox RSVP Campaign REST API

## 1. Overview & Conventions
- **Base URL**: `/api/`
- **Format**: JSON (`Content-Type: application/json` for REST calls, `multipart/form-data` for file uploads)
- **Authentication**: Session Authentication (`Cookie: sessionid=...`) with standard Django CSRF (`X-CSRFToken` header) or Token Authentication (`Authorization: Token ...`).
- **Standard Error Response**:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Human-readable explanation of error",
      "details": {}
    }
  }
  ```

---

## 2. Authentication Endpoints

### 2.1 Login
- **Endpoint**: `POST /api/auth/login/`
- **Auth**: None (Public)
- **Request Body**:
  ```json
  {
    "username": "event_manager",
    "password": "SecurePassword123"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "message": "Login successful",
    "user": {
      "id": 1,
      "username": "event_manager",
      "email": "events@globalvox.com"
    }
  }
  ```
- **Errors**: `400 Bad Request` (missing fields), `401 Unauthorized` (invalid credentials).

### 2.2 Current User
- **Endpoint**: `GET /api/auth/me/`
- **Auth**: Required
- **Response (200 OK)**: User profile object.

### 2.3 Logout
- **Endpoint**: `POST /api/auth/logout/`
- **Auth**: Required
- **Response (200 OK)**: `{"message": "Logged out successfully"}`

---

## 3. Invitee Management & Import Endpoints

### 3.1 Invitee CSV Import & Preview
- **Endpoint**: `POST /api/invitees/import/`
- **Auth**: Required
- **Content-Type**: `multipart/form-data`
- **Payload**:
  - `file`: CSV file (max 10MB)
  - `preview_only`: `true` | `false` (boolean string)
- **Validation**:
  - Requires headers: `name`, `phone`, `email` (optional `id`).
  - Row-by-row validation of phone format (E.164 compatible or standard digit strings), email format, and non-empty name.
- **Response (200 OK)**:
  ```json
  {
    "total_rows": 1000,
    "valid_count": 980,
    "invalid_count": 20,
    "imported_count": 980,
    "is_preview": false,
    "errors": [
      {
        "row": 14,
        "raw_data": {"id": "14", "name": "", "phone": "+919876543210", "email": "test@example.com"},
        "reasons": ["Name cannot be blank"]
      }
    ],
    "sample_valid": [
      {"name": "Rahul Sharma", "phone": "+919876543210", "email": "rahul@example.com"}
    ]
  }
  ```
- **Errors**: `400 Bad Request` (No file, invalid file extension, empty file, parse failure).

### 3.2 List Invitees
- **Endpoint**: `GET /api/invitees/?search=Rahul&page=1`
- **Auth**: Required
- **Response (200 OK)**: Paginated list of invitee records.

---

## 4. Campaign Management Endpoints

### 4.1 List Campaigns
- **Endpoint**: `GET /api/campaigns/`
- **Auth**: Required
- **Response (200 OK)**:
  ```json
  [
    {
      "id": 1,
      "name": "Annual Business Meet — RSVP",
      "event_name": "GlobalVox Annual Business Meet",
      "event_date": "2026-10-25",
      "event_location": "Ahmedabad",
      "objective": "AI agent should contact each invitee and determine attendance",
      "status": "DRAFT",
      "total_invitees": 1000,
      "created_at": "2026-09-14T10:00:00Z",
      "started_at": null,
      "completed_at": null
    }
  ]
  ```

### 4.2 Create Campaign
- **Endpoint**: `POST /api/campaigns/`
- **Auth**: Required
- **Request Body**:
  ```json
  {
    "name": "Annual Business Meet — RSVP",
    "event_name": "GlobalVox Annual Business Meet",
    "event_date": "2026-10-25",
    "event_location": "Ahmedabad",
    "objective": "AI calling objective to determine event attendance",
    "invitee_ids": [1, 2, 3, 4]
  }
  ```
- **Response (201 Created)**: Campaign entity with associated invitee count.
- **Errors**: `400 Bad Request` (missing name/event/date/location).

### 4.3 Get Campaign Details & Summary Metrics
- **Endpoint**: `GET /api/campaigns/<id>/`
- **Auth**: Required
- **Response (200 OK)**:
  ```json
  {
    "id": 1,
    "name": "Annual Business Meet — RSVP",
    "event_name": "GlobalVox Annual Business Meet",
    "event_date": "2026-10-25",
    "event_location": "Ahmedabad",
    "objective": "AI calling objective",
    "status": "RUNNING",
    "metrics": {
      "total_invitees": 1000,
      "confirmed": 620,
      "declined": 80,
      "undecided": 50,
      "pending": 200,
      "failed": 50
    },
    "created_at": "2026-09-14T10:00:00Z",
    "started_at": "2026-09-14T10:15:00Z",
    "completed_at": null
  }
  ```

### 4.4 Start Campaign Execution
- **Endpoint**: `POST /api/campaigns/<id>/start/`
- **Auth**: Required
- **Request Body**:
  ```json
  {
    "simulation_mode": "realistic"
  }
  ```
- **Behavior**:
  - Atomic verification of state. If `status != DRAFT`, returns `409 Conflict`.
  - Dispatches execution runner.
  - Updates campaign status to `RUNNING`, processes records, transitions to `COMPLETED`.
- **Response (200 OK)**:
  ```json
  {
    "message": "Campaign started successfully",
    "status": "RUNNING",
    "campaign_id": 1
  }
  ```
- **Errors**: `404 Not Found`, `409 Conflict` (Campaign is already RUNNING or COMPLETED).

---

## 5. Campaign Invitee & Call Results Endpoints

### 5.1 List Campaign Invitees
- **Endpoint**: `GET /api/campaigns/<id>/invitees/?rsvp_status=CONFIRMED&call_status=COMPLETED&search=Rahul&page=1`
- **Auth**: Required
- **Response (200 OK)**:
  ```json
  {
    "count": 620,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": 101,
        "invitee_id": 1,
        "name": "Rahul Sharma",
        "phone_masked": "+91 98765 ****0",
        "email": "rahul@example.com",
        "rsvp_status": "CONFIRMED",
        "call_status": "COMPLETED",
        "attempt_count": 1,
        "last_attempt_at": "2026-09-14T10:16:30Z",
        "notes": "Invitee confirmed attendance for 1 guest."
      }
    ]
  }
  ```

### 5.2 Individual Invitee Campaign History
- **Endpoint**: `GET /api/campaigns/<campaign_id>/invitees/<invitee_id>/`
- **Auth**: Required
- **Response (200 OK)**:
  ```json
  {
    "campaign_invitee_id": 101,
    "campaign": {
      "id": 1,
      "name": "Annual Business Meet — RSVP"
    },
    "invitee": {
      "id": 1,
      "name": "Rahul Sharma",
      "phone_masked": "+91 98765 ****0",
      "email": "rahul@example.com"
    },
    "rsvp_status": "CONFIRMED",
    "call_status": "COMPLETED",
    "attempt_count": 1,
    "notes": "Confirmed attendance with enthusiasm.",
    "attempts": [
      {
        "attempt_number": 1,
        "provider_call_id": "CALL-SIM-9827361",
        "status": "COMPLETED",
        "rsvp_outcome": "CONFIRMED",
        "duration_seconds": 45,
        "error_code": null,
        "error_message": null,
        "transcript_summary": "AI greeted Rahul Sharma and verified schedule. Invitee confirmed.",
        "started_at": "2026-09-14T10:15:45Z",
        "ended_at": "2026-09-14T10:16:30Z"
      }
    ]
  }
  ```
- **Errors**: `404 Not Found`.
