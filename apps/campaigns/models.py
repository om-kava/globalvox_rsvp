from django.db import models
from django.contrib.auth.models import User
from apps.invitees.models import Invitee

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

class Campaign(models.Model):
    """
    Represents an RSVP Calling Campaign for an upcoming business event.
    """
    name = models.CharField(max_length=255, db_index=True, help_text="Campaign name, e.g. Annual Business Meet — RSVP")
    event_name = models.CharField(max_length=255, help_text="Event name, e.g. GlobalVox Annual Business Meet")
    event_date = models.DateField(help_text="Scheduled date of the event")
    event_location = models.CharField(max_length=255, help_text="Event location, e.g. Ahmedabad")
    objective = models.TextField(blank=True, default="AI voice agent contacts invitees to collect RSVP responses.")
    status = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.DRAFT,
        db_index=True
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.status})"

    def calculate_metrics(self) -> dict:
        """
        Executes a single optimized SQL aggregation query across all campaign invitees.
        """
        from django.db.models import Count, Q
        stats = self.campaign_invitees.aggregate(
            total=Count('id'),
            confirmed=Count('id', filter=Q(rsvp_status=RSVPStatus.CONFIRMED)),
            declined=Count('id', filter=Q(rsvp_status=RSVPStatus.DECLINED)),
            undecided=Count('id', filter=Q(rsvp_status=RSVPStatus.UNDECIDED)),
            pending=Count('id', filter=Q(rsvp_status=RSVPStatus.PENDING) & ~Q(call_status=CallStatus.FAILED)),
            failed=Count('id', filter=Q(call_status=CallStatus.FAILED)),
        )
        return {
            'total_invitees': stats['total'] or 0,
            'confirmed': stats['confirmed'] or 0,
            'declined': stats['declined'] or 0,
            'undecided': stats['undecided'] or 0,
            'pending': stats['pending'] or 0,
            'failed': stats['failed'] or 0,
        }

class CampaignInvitee(models.Model):
    """
    Join model representing the association between a Campaign and an Invitee,
    tracking campaign-specific RSVP and call status.
    """
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='campaign_invitees')
    invitee = models.ForeignKey(Invitee, on_delete=models.CASCADE, related_name='campaign_participations')
    rsvp_status = models.CharField(
        max_length=20,
        choices=RSVPStatus.choices,
        default=RSVPStatus.PENDING,
        db_index=True
    )
    call_status = models.CharField(
        max_length=20,
        choices=CallStatus.choices,
        default=CallStatus.NOT_ATTEMPTED,
        db_index=True
    )
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Notes or summary captured from AI voice conversation")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['campaign', 'invitee'], name='unique_campaign_invitee')
        ]
        indexes = [
            models.Index(fields=['campaign', 'rsvp_status'], name='idx_camp_rsvp_status'),
            models.Index(fields=['campaign', 'call_status'], name='idx_camp_call_status'),
        ]

    def __str__(self):
        return f"{self.invitee.name} in {self.campaign.name} [{self.rsvp_status} / {self.call_status}]"
