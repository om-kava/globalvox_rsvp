# Architecture Decision Records (ADR) — GlobalVox RSVP System

## ADR-01: Framework Selection — Django & Django REST Framework
- **Date**: 2026-09-14
- **Context**: Need a robust, secure, production-ready backend for managing relational entities, authentication, file processing, and REST APIs within a 3-hour assessment window.
- **Options Considered**:
  1. FastAPI + SQLAlchemy
  2. Flask + Peewee
  3. Django + Django REST Framework
- **Chosen Option**: Django + Django REST Framework.
- **Reason**: Django provides built-in enterprise-grade security (CSRF, session management, secure password hashing, ORM injection protection), an established migration engine, seamless integration with DRF, and built-in transaction management.
- **Trade-off**: Slightly heavier footprint than microframeworks, but eliminates boilerplate and accelerates secure delivery.

---

## ADR-02: Frontend Architecture — Vanilla HTML5, CSS3, JavaScript
- **Date**: 2026-09-14
- **Context**: Must build a clean, responsive, intuitive UI for business users without introducing unnecessary build pipelines or framework overhead.
- **Options Considered**:
  1. Single Page Application with React/Next.js/Vue
  2. Server-rendered Django Templates with Vanilla JS and modern CSS
- **Chosen Option**: Vanilla HTML5, modern CSS3 (custom responsive design system), and Vanilla JavaScript (ES6+ modules).
- **Reason**: Strictly adheres to the chosen technology stack constraints. Zero node/npm compilation toolchains required to run the client, zero hydration delays, instant browser rendering, and full control over styling and DOM manipulation.
- **Trade-off**: Requires manual DOM updates instead of reactive state binding, mitigated by writing clean, modular rendering components.

---

## ADR-03: Database Engine — MySQL
- **Date**: 2026-09-14
- **Context**: Evaluation and persistence requirements.
- **Options Considered**:
  1. PostgreSQL
  2. SQLite
  3. MySQL
- **Chosen Option**: MySQL (via `django.db.backends.mysql`).
- **Reason**: Explicitly specified in the technology stack requirements. Provides robust relational integrity, ACID transactions, and composite indexing.
- **Trade-off**: Requires hosted MySQL server connectivity for Vercel deployment (handled via cloud MySQL instances).

---

## ADR-04: Calling Subsystem — Abstract CallingProvider with Mock Implementation
- **Date**: 2026-09-14
- **Context**: Assessment PDF specifies that an external AI voice calling service represents the calling system, but no external API specification, endpoints, or credentials are supplied in the assessment material.
- **Options Considered**:
  1. Invent a fake external HTTP calling service and mock server
  2. Integrate an unrequested third-party service (Twilio/Vapi)
  3. Implement an internal `CallingProvider` abstract interface with a realistic `MockCallingProvider`
- **Chosen Option**: Internal `CallingProvider` abstract base class with a pluggable `MockCallingProvider`.
- **Reason**: Adheres to strict instructions not to hallucinate third-party APIs or invent vendor contracts. Decouples business logic from telephony simulation. Future real providers can be plugged in seamlessly without altering campaign workflows.
- **Trade-off**: Simulation runs in-process or via lightweight handlers rather than external webhook round-trips.

---

## ADR-05: State Concurrency & Race Condition Defense
- **Date**: 2026-09-14
- **Context**: Multiple users or rapid duplicate clicks on "Start Campaign" could trigger concurrent calling processes, leading to duplicate calls and corrupted metrics.
- **Options Considered**:
  1. Frontend-only button disabling
  2. In-memory locking flag
  3. Database row-level locking (`select_for_update`) within atomic transaction
- **Chosen Option**: Database row-level locking (`select_for_update`) in an atomic transaction.
- **Reason**: Provides bulletproof backend enforcement that works even across multiple worker processes or distributed servers.
- **Trade-off**: Slight overhead of a database row lock during the initial transition from `DRAFT` to `RUNNING`.

---

## ADR-06: JWT & Dual-Mode Authentication Architecture
- **Date**: 2026-09-14
- **Context**: Need secure, stateless, decoupled API authentication while preserving seamless browser navigation and CSRF defenses.
- **Options Considered**:
  1. Session-only authentication
  2. Basic authentication
  3. JSON Web Tokens (JWT) via `djangorestframework-simplejwt` + Session fallback
- **Chosen Option**: Dual-Mode JWT + Session Authentication with Token Blacklisting.
- **Reason**: Standard Bearer token authentication allows external microservices, decoupled SPA frontends, and mobile clients to consume the API securely without cookie dependencies, while session fallback allows the local Django browser interface to operate smoothly. Token blacklisting guarantees that logged-out refresh tokens cannot be reused.
- **Trade-off**: Requires maintaining token blacklist database table and refreshing expired access tokens.
