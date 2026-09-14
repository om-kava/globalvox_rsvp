# GlobalVox RSVP Campaign Management System

## Project Overview
GlobalVox RSVP is an enterprise event management application designed for business teams to organize, execute, and monitor automated AI voice calling RSVP campaigns. The application enables users to import invitee lists from CSV files, validate and review contact data, configure event campaigns, initiate simulated AI voice calling sessions, track campaign results in real time (Confirmed, Declined, Undecided, Pending, Failed), and inspect individual invitee call attempt histories.

Developed for the **GlobalVox Software Engineering Assessment**.

---

## Planned Technology Stack

### Frontend
- **HTML5**: Clean semantic document structure.
- **CSS3**: Modern, responsive, accessible custom design system (Vanilla CSS, zero third-party utility dependencies).
- **Vanilla JavaScript (ES6+)**: Modular client architecture for API communication, dynamic DOM rendering, and real-time polling.

### Backend
- **Python (3.11+)**
- **Django 5.x**: Enterprise web framework providing ORM, session security, CSRF protection, and transaction management.
- **Django REST Framework (DRF)**: High-performance RESTful API endpoints, request validation, and serialization.

### Database
- **MySQL**: Relational data store with foreign key constraints, composite status indexes, and atomic state transitions via Django ORM.

### Calling Subsystem
- **Provider Abstraction (`CallingProvider`)**: Clean interface defining call dispatch and status retrieval contracts.
- **Mock Calling Provider (`MockCallingProvider`)**: In-process simulation of realistic AI voice calls, call durations, outcome distributions, and network/provider error states.

### Deployment Target
- **Vercel**: Serverless Python WSGI runtime hosting the Django application alongside static frontend assets, connected to a cloud-hosted MySQL database.

---

## Documentation Index
- [Master Plan](docs/MASTER_PLAN.md)
- [Requirements Specification](docs/REQUIREMENTS.md)
- [System Architecture](docs/ARCHITECTURE.md)
- [Database Design](docs/DATABASE.md)
- [REST API Specification](docs/API_SPEC.md)
- [Security Policies](docs/SECURITY.md)
- [Workflows & Lifecycle](docs/FLOW.md)
- [Master Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [Test Plan](docs/TEST_PLAN.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Architecture Decision Records (ADRs)](docs/DECISIONS.md)
- [Changelog](docs/CHANGELOG.md)
