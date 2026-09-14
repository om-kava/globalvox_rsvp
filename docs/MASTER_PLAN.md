# Master Plan — GlobalVox RSVP Campaign Management System

## 1. Project Objective
Build a small, secure, reliable, end-to-end working prototype for GlobalVox event and business team members to manage RSVP calling campaigns. The application enables users to authenticate, import invitee lists from CSV, validate and review records, create RSVP campaigns, initiate calling campaigns via a clean simulated AI calling provider interface, observe live progress and aggregated metrics, and inspect individual invitee call histories.

## 2. Source of Truth & Context
- **Document**: `globalvox task.pdf` (GlobalVox Software Engineering Assessment).
- **Core Domain**: AI Voice Agent RSVP calling campaign management for business events (e.g., GlobalVox Annual Business Meet).
- **Simulated Environment**: No real phone calls or conversational AI engines are built. A simulated AI calling provider represents the external calling system.
- **Evaluation Criteria**: Correctness, security, reliability, clean architecture, usability, assessment requirement compliance, deployment, documentation, and visual polish within a 3-hour scope.

## 3. Technology Stack
- **Frontend**: Vanilla HTML5, Vanilla CSS3 (modern business styling, responsive, accessible), Vanilla JavaScript (ES6+ modular, no React/Next/Vue).
- **Backend**: Python 3.11+, Django 5.x, Django REST Framework (DRF).
- **Database**: MySQL (Django ORM with strictly relational schema and database-level constraints; hosted MySQL for deployment).
- **Simulated Calling Provider**: Clean internal `CallingProvider` abstract base class with a pluggable `MockCallingProvider` simulating variable call durations, outcomes (Confirmed, Declined, Undecided), and failures/timeouts.
- **Deployment**: Vercel serverless WSGI runtime with static frontend routing and remote hosted MySQL.

## 4. Scope & Boundary
### In Scope
1. Secure business-user authentication (session/token-based with CSRF protection).
2. Invitee CSV import with multi-stage processing: parsing, strict validation, preview, deduplication, error reporting, and bulk persistence.
3. Campaign lifecycle management (Draft, Running, Completed) with concurrency/state lock protection.
4. Pluggable Calling Provider abstraction with realistic mock simulations (deterministic and probabilistic modes for reliable demoing).
5. Robust campaign execution engine that handles provider latency, network failures, and errors gracefully without crashing the campaign.
6. Business dashboard featuring high-level metrics (Total, Confirmed, Declined, Undecided, Pending, Failed), progress tracking, search, and filtering.
7. Detailed individual invitee inspection view with masked PII and call attempt timeline.
8. Comprehensive documentation and full compliance with assessment constraints.

### Out of Scope (Strict 3-Hour Scope)
1. Real telephony integration (Twilio, Retell, Vapi, Asterisk).
2. Live conversational LLM voice engines.
3. Microservices, Kafka, Redis, Celery (simulated execution and asynchronous batching patterns documented for production scale).
4. Multi-tenant complex RBAC (role-based access control beyond business-user / admin roles).
5. Payment gateways, email/SMS notifications.

## 5. Major Components
1. **Frontend Client**: Lightweight single-page / multi-view vanilla dashboard (`/static/` or template served) communicating with DRF endpoints.
2. **Authentication & Authorization**: Business user login, session management, permission checking, and ownership checks.
3. **Invitee Management Service**: File upload handling, CSV parsing, row validation, deduplication, error reporting.
4. **Campaign Service**: Campaign creation, state machine transitions, locking against duplicate execution.
5. **Calling Subsystem**:
   - `CallingProvider` interface: standardized contract (`initiate_call`, `get_call_status`).
   - `MockCallingProvider`: deterministic/probabilistic mock handling confirmed/declined/undecided/failure transitions.
6. **Execution Engine**: Processes campaign invitees sequentially or in controlled batches, captures `CallAttempt` records, updates `CampaignInvitee` state, and recalculates metrics.
7. **Analytics & Aggregation**: DB-level aggregations (`Count`, `Q` filters) for instant and accurate dashboard figures.

## 6. Implementation Phases (Planned)
- **Phase 0**: Analysis & Planning Documentation (Current Phase).
- **Phase 1**: Project Foundation (Django setup, DRF, environment configuration, base structure).
- **Phase 2**: Database Foundation (Models, migrations, indexes, constraints).
- **Phase 3**: Authentication & Authorization (Login/logout, route protection, user isolation).
- **Phase 4**: Invitee Import (CSV parsing, validation, preview, persistence).
- **Phase 5**: Campaign Management (CRUD, status lifecycle).
- **Phase 6**: Calling Provider Abstraction & Mock Simulation.
- **Phase 7**: Campaign Execution Engine (Idempotent runner, failure resilience).
- **Phase 8**: Results & Dashboard UI/API (Metrics, search, filters, pagination).
- **Phase 9**: Individual Invitee Inspection (Detail view, call history, masked PII).
- **Phase 10**: Security Review & Hardening.
- **Phase 11**: End-to-End Testing (Automated test suite + manual verification).
- **Phase 12**: UI Polish & Usability Refinement.
- **Phase 13**: Deployment Preparation (Vercel configuration, production DB).
- **Phase 14**: Final Audit & Submission Package.

## 7. Assumptions
1. **Missing Calling API Specification**: The PDF mentions a simulated calling service is provided, but no external URL, library, or credentials are supplied in the assessment bundle. As instructed, an internal `CallingProvider` abstraction with a configurable `MockCallingProvider` will simulate the calling behavior.
2. **Database Engine**: Development and production will target MySQL via Django ORM. For local development, if MySQL server is not locally running, environment variables will allow connecting to a remote MySQL instance or local fallback with exact same schema constraints.
3. **Deployment**: Target is Vercel serverless Python deployment connecting to a cloud-hosted MySQL database.
