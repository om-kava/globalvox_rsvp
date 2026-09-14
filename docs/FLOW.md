# System Workflows & Lifecycle — GlobalVox RSVP System

## 1. End-to-End User Flow

```text
┌────────────────┐
│   User Login   │ (Enter credentials -> Authenticate -> Session Established)
└───────┬────────┘
        │
        ▼
┌───────────────────────────┐
│     Campaign Dashboard    │ (View existing campaigns, summary cards, status badges)
└───────┬───────────────────┘
        │
        ├──▶ [Create New Campaign] (Event Name, Date, Location, Objective)
        │
        ├──▶ [Import Invitees] (Select CSV file -> Upload -> Parse -> Validation Preview)
        │             │
        │             ▼
        │     [Confirm Ingestion] (Valid invitees committed -> Assigned to Campaign)
        │
        ▼
┌───────────────────────────┐
│   Campaign In DRAFT State │ (Invitees linked, call status: NOT_ATTEMPTED)
└───────┬───────────────────┘
        │
        ▼
┌───────────────────────────┐
│     [Start Campaign]      │ (User initiates calling campaign)
└───────┬───────────────────┘
        │
        ▼
┌───────────────────────────┐
│   Real-time Execution     │ (Simulated AI voice calls processed)
│   & Progress Tracking     │ (Live counters update: Confirmed, Declined, Undecided, Failed)
└───────┬───────────────────┘
        │
        ▼
┌───────────────────────────┐
│   Campaign COMPLETED      │ (Final aggregated metrics displayed)
└───────┬───────────────────┘
        │
        ├──▶ [Filter & Search Results] (Filter by Confirmed, Failed, etc.)
        │
        └──▶ [Click Invitee Row] ──▶ Open Detail View (Phone, Call History, Logs, Errors)
```

---

## 2. Technical Execution Flow

```text
Browser Client                     DRF API View                   CampaignExecutionService        CallingProvider Adapter          Database (MySQL)
      │                                 │                                    │                               │                          │
      │── POST /campaigns/1/start/ ────▶│                                    │                               │                          │
      │                                 │── acquire lock & verify state ───────────────────────────────────────────────────────────────▶│ SELECT FOR UPDATE
      │                                 │                                    │                               │                          │ Status: DRAFT -> RUNNING
      │                                 │── dispatch runner ────────────────▶│                               │                          │
      │◀─ 200 OK (RUNNING) ─────────────│                                    │                               │                          │
      │                                                                      │                               │                          │
      │                                                                      │── fetch pending invitees ───────────────────────────────▶│
      │                                                                      │◀─ return CampaignInvitee list ───────────────────────────│
      │                                                                      │                               │                          │
      │                                                                      │── loop invitees:              │                          │
      │                                                                      │    provider.initiate_call() ─▶│                          │
      │                                                                      │    (simulate AI dial & talk)  │                          │
      │                                                                      │◀── return CallResult ─────────│                          │
      │                                                                      │    (status, outcome, notes)   │                          │
      │                                                                      │                               │                          │
      │                                                                      │── persist CallAttempt ──────────────────────────────────▶│ INSERT CallAttempt
      │                                                                      │── update CampaignInvitee ───────────────────────────────▶│ UPDATE CampaignInvitee
      │                                                                      │    (rsvp_status, call_status) │                          │
      │                                                                      │                               │                          │
      │                                                                      │── all processed:              │                          │
      │                                                                      │    transition to COMPLETED ─────────────────────────────▶│ UPDATE Campaign
      │                                                                      │                               │                          │ Status = COMPLETED
```

---

## 3. Failure & Exception Handling Flow

The external AI voice calling environment is inherently prone to partial failures (unreachable phones, call drops, network timeouts, invalid recipient numbers).

```text
                        ┌──────────────────────────────┐
                        │   Dispatch Call to Invitee   │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │   Provider Execution Check   │
                        └──────────────┬───────────────┘
                                       │
               ┌───────────────────────┴───────────────────────┐
               ▼                                               ▼
     [Success: Connected]                            [Failure Encountered]
               │                                               │
     ┌───────────────────┐                           ┌───────────────────────────┐
     │ Determine RSVP:   │                           │ Classify Failure Type:    │
     │ - CONFIRMED       │                           │ - NETWORK_TIMEOUT         │
     │ - DECLINED        │                           │ - BUSY / NO_ANSWER        │
     │ - UNDECIDED       │                           │ - INVALID_NUMBER          │
     └─────────┬─────────┘                           │ - PROVIDER_CRASH          │
               │                                     └─────────────┬─────────────┘
               │                                                   │
               ▼                                                   ▼
     ┌───────────────────────────┐                   ┌───────────────────────────┐
     │ CallAttempt:              │                   │ CallAttempt:              │
     │  status: COMPLETED        │                   │  status: FAILED           │
     │  rsvp_outcome: outcome    │                   │  rsvp_outcome: FAILED     │
     │  error: null              │                   │  error_code: code         │
     └─────────┬─────────────────┘                   │  error_message: message   │
               │                                     └─────────────┬─────────────┘
               │                                                   │
               ▼                                                   ▼
     ┌───────────────────────────┐                   ┌───────────────────────────┐
     │ CampaignInvitee:          │                   │ CampaignInvitee:          │
     │  call_status: COMPLETED   │                   │  call_status: FAILED      │
     │  rsvp_status: outcome     │                   │  rsvp_status: PENDING     │
     └─────────┬─────────────────┘                   └─────────────┬─────────────┘
               │                                                   │
               └───────────────────────┬───────────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │  Continue to Next Invitee    │
                        │ (Campaign is NEVER halted    │
                        │   by a single failure)       │
                        └──────────────────────────────┘
```

---

## 4. Invitee CSV Import Flow

```text
Admin uploads CSV file
   ↓
Validate Content-Type & File Size (<= 10MB)
   ↓
Stream rows via csv.DictReader
   ↓
Row Validation:
   ├── Check required keys: "name", "phone", "email"
   ├── Validate phone format (regex/E.164)
   ├── Validate email format (EmailValidator)
   └── Sanitize string inputs
   ↓
Fork evaluation:
   ├── If Invalid: Add to `errors[]` with row index and exact error messages
   └── If Valid: Check duplicate phone in batch; add to `valid_batch[]`
   ↓
Preview Mode?
   ├── If YES: Return validation statistics and sample preview without DB writes
   └── If NO:
         ├── Bulk insert unique new `Invitee` records in MySQL
         ├── Link to Campaign via `CampaignInvitee` records
         └── Return import confirmation count and error log
```
