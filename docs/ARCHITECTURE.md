# System Architecture — GlobalVox RSVP Campaign Management System

## 1. High-Level Architecture Overview

```text
Browser Client (HTML5 / Vanilla CSS3 / Vanilla JavaScript)
   │
   │  HTTPS / JSON / Session & CSRF
   ▼
Web Server / WSGI (Vercel Serverless / Gunicorn)
   │
   ▼
Django Core & Security Middleware
   │
   ▼
Django REST Framework (Views, Serializers, Permissions)
   │
   ▼
Service Layer (CampaignService, InviteeService, ExecutionService)
   │
   ├──▶ Calling Provider Abstraction (CallingProvider Interface)
   │         │
   │         ▼
   │     MockCallingProvider (Simulated Call Engine & Latency/Outcome Matrix)
   │         [Future: Real Voice AI Provider Adapter (e.g., Twilio/Vapi/GlobalVox Voice)]
   │
   ▼
Django ORM / Query Optimization (Bulk operations, DB aggregation)
   │
   ▼
MySQL Database (Relational integrity, Foreign Keys, Indexes, Constraints)
```

---

## 2. Component Design

### 2.1 Frontend Architecture
- **Tech**: Semantic HTML5, Vanilla CSS3 (custom design system, flexbox/grid, accessible colors, high contrast, clean business look), Vanilla JS (ES6+ modular class/module pattern).
- **No external frameworks**: No React, Next.js, Vue, Angular, or Tailwind.
- **Client Capabilities**:
  - Modular API client (`api.js`) managing authentication, CSRF tokens, and JSON requests.
  - State rendering modules for Dashboard, Campaign Creation, Invitee CSV Upload, and Invitee Details Modal.
  - Auto-refresh polling during active campaign execution to reflect real-time progress.
  - Client-side data hygiene: safe DOM rendering (`textContent`, DOM nodes) to eliminate XSS.

### 2.2 Backend Architecture (Django & DRF)
- **Django Apps**:
  - `accounts`: User authentication, session/token management, authorization decorators.
  - `campaigns`: Campaign entity, lifecycle management, analytics calculation.
  - `invitees`: Invitee storage, CSV ingestion, validation, deduplication.
  - `calling`: Calling provider abstract base class, mock simulation engine, call attempt history logging.
- **Service Layer Pattern**:
  - Views remain thin controllers handling HTTP serialization, validation, and status codes.
  - Core domain logic resides in dedicated services:
    - `InviteeImportService`: Stream/parse CSV, apply validation rules, format error reports, perform atomic bulk insertions.
    - `CampaignExecutionService`: Transition state atomically, orchestrate provider calls, log individual attempts, compute statuses.
    - `AnalyticsService`: Compute campaign summary counts using single SQL aggregation queries (`filter=Q(...)`).

### 2.3 Calling Provider Subsystem
```text
                  ┌──────────────────────────────┐
                  │    CallingProvider (ABC)     │
                  ├──────────────────────────────┤
                  │ + initiate_call(params)      │
                  │ + get_call_status(call_id)   │
                  └──────────────┬───────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
     ┌──────────────────────┐        ┌──────────────────────┐
     │  MockCallingProvider │        │ RealVoiceAIProvider  │
     ├──────────────────────┤        ├──────────────────────┤
     │ - Simulates latency  │        │ - Connects to API    │
     │ - Realistic outcomes │        │ - Handles webhooks   │
     │ - Simulates failures │        │ - WebRTC / SIP       │
     └──────────────────────┘        └──────────────────────┘
```
- The `CallingProvider` abstract base class defines:
  ```python
  class CallingProvider(ABC):
      @abstractmethod
      def initiate_call(self, invitee_id: str, name: str, phone: str, campaign_context: dict) -> CallResult:
          pass
  ```
- `MockCallingProvider`:
  - Implements the contract with deterministic seed capability or realistic distribution (e.g., 62% confirmed, 8% declined, 5% undecided, 20% pending/unreachable, 5% failed).
  - Simulates call metadata: provider call ID, duration (seconds), transcript summary notes, and error codes.
  - Decoupled from the campaign execution engine, enabling trivial replacement with an actual API client.

### 2.4 Database Architecture
- Strictly relational schema in MySQL.
- Foreign key constraints ensure referential integrity.
- Composite indexes on `(campaign_id, rsvp_status)` and `(campaign_id, call_status)` accelerate dashboard metrics on tables with 100,000+ rows.

---

## 3. Data Flow
1. **User Authentication**:
   - Browser POST `/api/auth/login/` with credentials.
   - Server returns session/token + CSRF cookie.
2. **Invitee List Ingestion**:
   - Business user uploads CSV at `/api/invitees/import/`.
   - `InviteeImportService` streams lines, validates each row against name/phone/email constraints.
   - Returns validation summary: count valid, count invalid with line-numbered error reasons.
   - Upon confirmation or direct import, valid invitees are committed via bulk insert.
3. **Campaign Creation**:
   - User posts campaign details (name, event date, location, objective) and associates imported invitees.
   - `CampaignInvitee` records created in `DRAFT` / `PENDING` state.
4. **Campaign Execution**:
   - User initiates `/api/campaigns/<id>/start/`.
   - Backend acquires lock on campaign row, verifies `status == 'DRAFT'`, transitions to `RUNNING`.
   - Campaign runner iterates through `CampaignInvitee` records:
     - Dispatches call to `CallingProvider.initiate_call(...)`.
     - Logs `CallAttempt` record with timestamps, duration, provider ID, status, and error notes.
     - Updates `CampaignInvitee` with latest `rsvp_status`, `call_status`, and `attempt_count`.
   - Upon completion of batch, transitions campaign to `COMPLETED`.
5. **Real-time Monitoring & Inspection**:
   - Frontend polls `/api/campaigns/<id>/metrics/` to update dashboard numbers.
   - User clicks individual invitee -> requests `/api/campaigns/<id>/invitees/<invitee_id>/` to view detailed history and call attempts.

---

## 4. Deployment Architecture
- **Target Platform**: Vercel.
- **Frontend**: Served as static assets (`public/` or Django staticfiles route).
- **Backend API**: Django WSGI application deployed through Vercel serverless Python runtime (`api/index.py` or `vercel.json` config).
- **Database**: Cloud-hosted MySQL instance (e.g. Aiven, PlanetScale MySQL, Railway MySQL, or AWS RDS) configured via environment variables (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`).

---

## 5. Future Scaling Architecture (Production Roadmap)
To handle 100,000+ invitees without blocking HTTP requests:
```text
Client ──▶ Django API ──▶ Redis / Celery Task Queue
                                │
                                ▼
                       Worker Cluster (N instances)
                                │
                      Rate Limiter / Dispatcher
                                │
                                ▼
                    External Voice AI Gateway
                                │
                                ▼
                    Webhook Ingestion Endpoint
                                │
                                ▼
                    MySQL Database (Read Replicas)
```
- **Job Queue**: Decouple campaign initiation from synchronous HTTP execution using Celery or AWS SQS.
- **Worker Concurrency**: Worker processes consume batches of invitees respecting telephony rate limits (e.g. 50 calls/sec).
- **Webhooks**: Provider asynchronously pushes call termination events to a high-throughput webhook receiver.
- **Partitioning**: Partition `CallAttempt` table by date or campaign ID for efficient archiving.
