# Database Design Specification — GlobalVox RSVP System

## 1. Overview
The database layer uses MySQL with the Django ORM. The schema strictly decouples persistent contact entities (`Invitee`) from campaign-specific engagement states (`CampaignInvitee`) and historical call execution records (`CallAttempt`).

---

## 2. Entity-Relationship Diagram (Logical)

```text
       ┌────────────────────────┐              ┌────────────────────────┐
       │        Campaign        │              │        Invitee         │
       ├────────────────────────┤              ├────────────────────────┤
       │ id (PK)                │              │ id (PK)                │
       │ name                   │              │ name                   │
       │ event_name             │              │ phone                  │
       │ event_date             │              │ email                  │
       │ event_location         │              │ created_at             │
       │ objective              │              │ updated_at             │
       │ status                 │              └───────────┬────────────┘
       │ created_at             │                          │
       │ started_at             │                          │
       │ completed_at           │                          │
       └───────────┬────────────┘                          │
                   │                                       │
                   │ 1                                     │ 1
                   │                                       │
                   │ N                                     │ N
                   ▼                                       ▼
       ┌────────────────────────────────────────────────────────┐
       │                    CampaignInvitee                     │
       ├────────────────────────────────────────────────────────┤
       │ id (PK)                                                │
       │ campaign_id (FK -> Campaign.id)                        │
       │ invitee_id (FK -> Invitee.id)                          │
       │ rsvp_status (PENDING | CONFIRMED | DECLINED | UNDECIDED)│
       │ call_status (NOT_ATTEMPTED | IN_PROGRESS | COMPLETED | FAILED)│
       │ attempt_count                                          │
       │ last_attempt_at                                        │
       │ notes / transcript_summary                             │
       │ updated_at                                             │
       └───────────────────────────┬────────────────────────────┘
                                   │ 1
                                   │
                                   │ N
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │                      CallAttempt                       │
       ├────────────────────────────────────────────────────────┤
       │ id (PK)                                                │
       │ campaign_invitee_id (FK -> CampaignInvitee.id)         │
       │ attempt_number                                         │
       │ provider_call_id                                       │
       │ status (IN_PROGRESS | COMPLETED | FAILED)              │
       │ rsvp_outcome (PENDING | CONFIRMED | DECLINED | UNDECIDED | FAILED)│
       │ duration_seconds                                       │
       │ error_code / error_message                             │
       │ notes                                                  │
       │ started_at                                             │
       │ ended_at                                               │
       └────────────────────────────────────────────────────────┘
```

---

## 3. Entity Definitions

### 3.1 `Campaign`
Represents an event RSVP calling campaign.

| Field | Type | Attributes | Description |
|---|---|---|---|
| `id` | `BigAutoField` | PK | Auto-incrementing primary key |
| `name` | `CharField(255)` | indexed | e.g. "Annual Business Meet — RSVP" |
| `event_name` | `CharField(255)` | not null | e.g. "GlobalVox Annual Business Meet" |
| `event_date` | `DateField` | not null | e.g. "2026-10-25" |
| `event_location` | `CharField(255)` | not null | e.g. "Ahmedabad" |
| `objective` | `TextField` | blank=True | "AI agent calls invitees to determine attendance" |
| `status` | `CharField(20)` | indexed | `DRAFT`, `RUNNING`, `COMPLETED` (default: `DRAFT`) |
| `created_by` | `ForeignKey(User)` | nullable | Reference to business user who created it |
| `created_at` | `DateTimeField` | auto_now_add | Creation timestamp |
| `started_at` | `DateTimeField` | null=True, blank=True | Timestamp when campaign was started |
| `completed_at` | `DateTimeField` | null=True, blank=True | Timestamp when execution concluded |

### 3.2 `Invitee`
Represents a unique contact in the organization address book.

| Field | Type | Attributes | Description |
|---|---|---|---|
| `id` | `BigAutoField` | PK | Auto-incrementing primary key |
| `external_id` | `CharField(100)` | null=True, blank=True, index | Optional ID provided in CSV input |
| `name` | `CharField(255)` | not null | Invitee's full name |
| `phone` | `CharField(32)` | not null, indexed | E.164 normalized phone number |
| `email` | `EmailField(254)` | not null, indexed | Email address |
| `created_at` | `DateTimeField` | auto_now_add | Creation timestamp |
| `updated_at` | `DateTimeField` | auto_now | Modification timestamp |

**Indexes & Constraints**:
- Unique constraint on `phone` (or scoped uniqueness per user/organization).

### 3.3 `CampaignInvitee`
Join entity binding an Invitee to a specific Campaign, holding campaign-specific RSVP and execution status.

| Field | Type | Attributes | Description |
|---|---|---|---|
| `id` | `BigAutoField` | PK | Primary key |
| `campaign` | `ForeignKey(Campaign)` | on_delete=CASCADE | Reference to campaign |
| `invitee` | `ForeignKey(Invitee)` | on_delete=CASCADE | Reference to invitee |
| `rsvp_status` | `CharField(20)` | indexed | `PENDING`, `CONFIRMED`, `DECLINED`, `UNDECIDED` (default: `PENDING`) |
| `call_status` | `CharField(20)` | indexed | `NOT_ATTEMPTED`, `IN_PROGRESS`, `COMPLETED`, `FAILED` (default: `NOT_ATTEMPTED`) |
| `attempt_count` | `PositiveIntegerField` | default=0 | Total number of call attempts made |
| `last_attempt_at` | `DateTimeField` | null=True, blank=True | Timestamp of most recent attempt |
| `notes` | `TextField` | blank=True | Summary notes from the AI conversation |
| `updated_at` | `DateTimeField` | auto_now | Last update timestamp |

**Constraints & Indexes**:
- `UniqueConstraint(fields=['campaign', 'invitee'], name='unique_campaign_invitee')`
- Index on `(campaign, rsvp_status)` for real-time dashboard aggregation.
- Index on `(campaign, call_status)` for queue filtering.

### 3.4 `CallAttempt`
Audit trail of every simulated call attempt dispatched to the calling provider.

| Field | Type | Attributes | Description |
|---|---|---|---|
| `id` | `BigAutoField` | PK | Primary key |
| `campaign_invitee` | `ForeignKey(CampaignInvitee)` | on_delete=CASCADE | Associated campaign invitee |
| `attempt_number` | `PositiveIntegerField` | default=1 | 1st, 2nd, or nth attempt |
| `provider_call_id` | `CharField(128)` | indexed | Unique identifier from calling provider |
| `status` | `CharField(20)` | not null | `IN_PROGRESS`, `COMPLETED`, `FAILED` |
| `rsvp_outcome` | `CharField(20)` | not null | Result: `CONFIRMED`, `DECLINED`, `UNDECIDED`, `FAILED` |
| `duration_seconds` | `PositiveIntegerField` | default=0 | Call duration in seconds |
| `error_code` | `CharField(64)` | blank=True | e.g. `NETWORK_TIMEOUT`, `BUSY`, `USER_DROP` |
| `error_message` | `TextField` | blank=True | Detailed failure description |
| `transcript_summary`| `TextField` | blank=True | AI agent conversation log summary |
| `started_at` | `DateTimeField` | not null | Timestamp call was initiated |
| `ended_at` | `DateTimeField` | null=True, blank=True | Timestamp call concluded |

**Indexes**:
- Index on `(campaign_invitee, attempt_number)`
- Index on `provider_call_id`

---

## 4. Controlled Status Constants

```python
class CampaignStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'

class RSVPStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    DECLINED = 'DECLINED', 'Declined'
    UNDECIDED = 'UNDECIDED', 'Undecided'

class CallStatus(models.TextChoices):
    NOT_ATTEMPTED = 'NOT_ATTEMPTED', 'Not Attempted'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
```

---

## 5. Performance & Scale Optimizations
1. **Aggregations**:
   Metrics query uses single SQL aggregation:
   ```python
   CampaignInvitee.objects.filter(campaign_id=cid).aggregate(
       total=Count('id'),
       confirmed=Count('id', filter=Q(rsvp_status='CONFIRMED')),
       declined=Count('id', filter=Q(rsvp_status='DECLINED')),
       undecided=Count('id', filter=Q(rsvp_status='UNDECIDED')),
       pending=Count('id', filter=Q(rsvp_status='PENDING', call_status='NOT_ATTEMPTED')),
       failed=Count('id', filter=Q(call_status='FAILED')),
   )
   ```
2. **Bulk Insertion**: `bulk_create` with batch sizes (e.g., 1,000 items) for rapid ingestion of large CSV imports.
3. **Query Select Related**: `select_related('invitee', 'campaign')` avoids N+1 queries during listing.
