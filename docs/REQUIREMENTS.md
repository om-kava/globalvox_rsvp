# Requirements Specification — GlobalVox RSVP Campaign

## 1. Explicit Requirements (Directly from `globalvox task.pdf`)
1. **Context & Objective**: Build a working prototype application that the GlobalVox team uses to manage and execute an RSVP calling campaign and track results for an upcoming business event.
2. **AI Voice Agent Simulation**: The AI agent calls each person to determine if they will attend, will not attend, or are unsure / need to decide later.
3. **No Real Calls**: No real calls need to be made. The conversation is handled by a simulated calling service that represents an external AI calling provider.
4. **Invitee List Schema**:
   - Fields: `id`, `name`, `phone`, `email`
   - Example row format: `1,Rahul Sharma,+919876543210,rahul@example.com`
   - Data ingestion: The application must allow the event team to bring this list into the system.
   - Scale: The list may contain a small number of invitees or a very large number (e.g. 100, 1,000, 10,000, 100,000+).
   - Validation: Must handle invalid or incomplete data appropriately without silently crashing.
5. **Campaign Creation**:
   - Business team can create an RSVP campaign with metadata:
     - Event Name (e.g., "GlobalVox Annual Business Meet")
     - Event Date (e.g., "25 October 2026")
     - Event Location (e.g., "Ahmedabad")
     - Campaign Name (e.g., "Annual Business Meet — RSVP")
     - AI Calling Objective: contact each invitee and determine attendance.
6. **Campaign Execution**:
   - User can start the RSVP campaign.
   - System attempts to process invitees through the simulated calling service.
7. **RSVP Results & Metrics**:
   - The team needs to understand the campaign outcome.
   - At minimum, the system must distinguish between:
     - Confirmed attendance
     - Declined
     - Undecided
     - Have not yet been successfully contacted (Pending)
   - Dashboard example in PDF:
     - Total Invitees: 1,000
     - Confirmed: 620
     - Declined: 80
     - Undecided: 50
     - Pending: 200
     - Failed: 50
8. **Individual Invitee View**:
   - View what happened with an individual invitee:
     - Name (e.g., Rahul Sharma)
     - Phone (e.g., +91XXXXXXXXXX)
     - Campaign (e.g., Annual Business Meet — RSVP)
     - Status (e.g., Confirmed)
     - Call (e.g., Completed)
     - Call history/attempts and errors.
9. **Calling Service Imperfection Handling**:
   - The external calling service may not always behave perfectly.
   - Application must handle unexpected behavior, failures, and timeouts gracefully.
10. **Target User Persona**:
    - GlobalVox event / business team member, not a developer.
    - Clean, intuitive presentation of campaigns, stats, and problems.
11. **Deployment & Delivery**:
    - Live accessible Vercel deployment URL.
    - Complete codebase as a ZIP.
    - Email submission to `shivi.sharma@globalvoxinc.com` and `devvrat.solanki@globalvoxinc.com`.
    - Comprehensive `README.md` with AI usage disclosure.
    - Assessment time budget: 3 hours.

---

## 2. Derived Technical Requirements
1. **Relational Database Design**:
   - Separate models for `Campaign`, `Invitee`, `CampaignInvitee` (join entity tracking campaign-specific invitee state), and `CallAttempt` (audit trail of each call).
   - Indexed foreign keys and composite status indexes to support fast dashboard metric aggregations.
2. **REST API Architecture**:
   - Standardized JSON REST API using Django REST Framework for campaign lifecycle, file uploads, metric retrieval, and invitee details.
3. **Data Ingestion Engine**:
   - Multipart file upload supporting standard CSV formats.
   - Strict field validation (E.164 / valid phone formats, RFC-compliant email, mandatory name, non-empty fields).
   - Atomic or controlled transaction handling with clear feedback on valid vs. rejected records.
4. **State Machine Separation**:
   - Separate technical call status (`NOT_ATTEMPTED`, `IN_PROGRESS`, `COMPLETED`, `FAILED`) from business RSVP status (`PENDING`, `CONFIRMED`, `DECLINED`, `UNDECIDED`).
   - Campaign lifecycle states (`DRAFT`, `RUNNING`, `COMPLETED`).
5. **Execution Idempotency & Concurrency Locks**:
   - Prevent simultaneous double-start requests on the same campaign using database locking (`select_for_update` / atomic status transitions).
6. **Provider Abstraction Pattern**:
   - Abstract base class defining `CallingProvider` with standardized request/response data classes.
   - Clean dependency injection allowing easy swap from mock to future real vendor SDKs.
7. **Privacy & Security**:
   - Phone masking on UI presentations (e.g., `+91 98765 ****0`).
   - Strict CSRF and authentication token validation.
   - Prevention of SQL Injection, XSS, and IDOR.

---

## 3. Assumptions
1. **Calling Service Contract [ASSUMPTION]**: Because no external calling server or API endpoints are packaged with the assessment files, we assume an internal Python provider interface with a mock implementation simulating network calls, varying call lengths, and response distributions matching the PDF example.
2. **Execution Timing [ASSUMPTION]**: To provide an interactive experience during the evaluation, the simulated call runner will execute rapidly (with optional micro-delays or batch steps) so the evaluator can observe status changes from Draft -> Running -> Completed without waiting hours.
3. **Authentication [ASSUMPTION]**: A lightweight authentication model (business user credentials) will protect all campaign management endpoints and the UI.
4. **Database Engine [ASSUMPTION]**: Local and production environments will configure MySQL via `django.db.backends.mysql` with environment variables.

---

## 4. Out of Scope (Strict 3-Hour Scope)
- Real PSTN/VoIP phone calls or WebRTC integration.
- Training or hosting real conversational AI / LLM models.
- Celery / Redis worker clusters (documented as production scale evolution).
- Multi-tenant enterprise RBAC and complex billing.
- Real-time WebSockets (replaced with clean REST polling for live progress).
- Native mobile applications.
