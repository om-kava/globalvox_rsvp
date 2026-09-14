from django.db import transaction
from django.utils import timezone
from typing import Optional, Dict, Any

from apps.campaigns.models import Campaign, CampaignInvitee, CampaignStatus, RSVPStatus, CallStatus
from apps.invitees.models import Invitee
from apps.calling.models import CallAttempt, CallAttemptStatus
from apps.calling.base import CallingProvider, CallRequest
from apps.calling.mock_provider import MockCallingProvider

class CampaignExecutionConflictError(Exception):
    """Raised when a campaign cannot be started due to state conflicts."""
    pass

class CampaignExecutor:
    """
    Orchestrates calling campaign execution with database concurrency locks,
    telephony provider dispatch, audit logging, and failure resilience.
    """

    def __init__(self, provider: Optional[CallingProvider] = None, seed: Optional[int] = None):
        self.provider = provider or MockCallingProvider(seed=seed)

    def start_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """
        Atomically locks the campaign row, transitions state from DRAFT -> RUNNING,
        processes all enrolled invitees through the calling provider, records CallAttempts,
        and transitions state to COMPLETED.
        """
        # Step 1: Concurrency-safe atomic state acquisition
        with transaction.atomic():
            try:
                campaign = Campaign.objects.select_for_update().get(id=campaign_id)
            except Campaign.DoesNotExist:
                raise ValueError(f"Campaign with ID {campaign_id} does not exist.")

            if campaign.status == CampaignStatus.RUNNING:
                raise CampaignExecutionConflictError(
                    f"Campaign '{campaign.name}' cannot be started because it is already actively running."
                )

            # Check if there are pending invitees to call
            pending_count = campaign.campaign_invitees.filter(
                call_status=CallStatus.NOT_ATTEMPTED
            ).count()

            if pending_count == 0:
                if campaign.campaign_invitees.count() == 0:
                    raise CampaignExecutionConflictError(
                        f"Campaign '{campaign.name}' has no invitees enrolled. Please import a CSV for this campaign first."
                    )
                else:
                    raise CampaignExecutionConflictError(
                        f"All invitees in Campaign '{campaign.name}' have already been called. No pending calls remaining."
                    )

            campaign.status = CampaignStatus.RUNNING
            if not campaign.started_at:
                campaign.started_at = timezone.now()
            campaign.save(update_fields=['status', 'started_at'])

        # Step 2: Fetch only pending invitees that have NOT been attempted yet
        participations = campaign.campaign_invitees.select_related('invitee').filter(
            call_status=CallStatus.NOT_ATTEMPTED
        )

        calls_dispatched = 0
        successful_calls = 0
        failed_calls = 0

        # Step 3: Process invitee calls
        for ci in participations:
            calls_dispatched += 1
            attempt_num = ci.attempt_count + 1
            start_time = timezone.now()

            # Construct standardized call request
            call_req = CallRequest(
                invitee_id=ci.invitee.id,
                name=ci.invitee.name,
                phone=ci.invitee.phone,
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                event_name=campaign.event_name,
                attempt_number=attempt_num
            )

            # Dispatch call to telephony provider (failure resilient)
            try:
                call_resp = self.provider.initiate_call(call_req)
            except Exception as exc:
                # Fallback if provider raises unexpected crash exception
                from apps.calling.base import CallResponse
                call_resp = CallResponse(
                    provider_call_id=f"CALL-ERR-{ci.id}",
                    status=CallAttemptStatus.FAILED,
                    rsvp_outcome='FAILED',
                    duration_seconds=0,
                    error_code='UNHANDLED_PROVIDER_EXCEPTION',
                    error_message=str(exc),
                    transcript_summary=f"Telephony exception during dispatch: {str(exc)}",
                    is_success=False
                )

            end_time = timezone.now()

            # Record CallAttempt audit trail
            CallAttempt.objects.create(
                campaign_invitee=ci,
                attempt_number=attempt_num,
                provider_call_id=call_resp.provider_call_id,
                status=call_resp.status,
                rsvp_outcome=call_resp.rsvp_outcome if call_resp.rsvp_outcome in RSVPStatus.values else RSVPStatus.PENDING,
                duration_seconds=call_resp.duration_seconds,
                error_code=call_resp.error_code,
                error_message=call_resp.error_message,
                transcript_summary=call_resp.transcript_summary,
                started_at=start_time,
                ended_at=end_time
            )

            # Update CampaignInvitee status
            ci.attempt_count = attempt_num
            ci.last_attempt_at = end_time
            ci.notes = call_resp.transcript_summary

            if call_resp.status == CallAttemptStatus.COMPLETED:
                successful_calls += 1
                if call_resp.rsvp_outcome in [RSVPStatus.CONFIRMED, RSVPStatus.DECLINED, RSVPStatus.UNDECIDED]:
                    ci.rsvp_status = call_resp.rsvp_outcome
                    ci.call_status = CallStatus.COMPLETED
                else:
                    # Unreachable / Voicemail / No Answer -> Remains PENDING
                    ci.rsvp_status = RSVPStatus.PENDING
                    ci.call_status = CallStatus.COMPLETED
            else:
                # Call failed or timed out -> call_status = FAILED, rsvp_status remains PENDING
                failed_calls += 1
                ci.call_status = CallStatus.FAILED
                ci.rsvp_status = RSVPStatus.PENDING

            ci.save(update_fields=['attempt_count', 'last_attempt_at', 'notes', 'rsvp_status', 'call_status'])

        # Step 4: Finalize campaign completion
        campaign.status = CampaignStatus.COMPLETED
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=['status', 'completed_at'])

        return {
            'campaign_id': campaign.id,
            'campaign_name': campaign.name,
            'status': campaign.status,
            'started_at': campaign.started_at,
            'completed_at': campaign.completed_at,
            'calls_dispatched': calls_dispatched,
            'successful_calls': successful_calls,
            'failed_calls': failed_calls,
            'metrics': campaign.calculate_metrics()
        }
