import random
import uuid
from typing import Optional

from apps.calling.base import CallingProvider, CallRequest, CallResponse
from apps.campaigns.models import RSVPStatus, CallStatus
from apps.calling.models import CallAttemptStatus

class MockCallingProvider(CallingProvider):
    """
    High-fidelity simulation of an external AI Voice Calling Provider.
    Implements the imperfect calling behavior described in the assessment:
    - Variable conversation durations
    - Realistic outcome distribution (Confirmed, Declined, Undecided, Unreachable/Pending, Failed)
    - Simulated transient errors, network timeouts, and busy lines
    - Supports deterministic seeding for predictable automated tests.
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def initiate_call(self, request: CallRequest) -> CallResponse:
        call_id = f"CALL-SIM-{uuid.uuid4().hex[:10].upper()}"

        # Roll for outcome based on the assessment's typical distribution:
        # 62% Confirmed, 8% Declined, 5% Undecided, 20% Unreachable (Pending), 5% Failed
        roll = self.rng.random()

        if roll < 0.62:
            # 1. CONFIRMED ATTENDANCE (62%)
            duration = self.rng.randint(35, 95)
            return CallResponse(
                provider_call_id=call_id,
                status=CallAttemptStatus.COMPLETED,
                rsvp_outcome=RSVPStatus.CONFIRMED,
                duration_seconds=duration,
                transcript_summary=(
                    f"AI Voice Agent connected with {request.name}. Invitee confirmed they will "
                    f"attend {request.event_name} and noted their arrival time."
                ),
                is_success=True
            )

        elif roll < 0.70:
            # 2. DECLINED (8%)
            duration = self.rng.randint(20, 50)
            reasons = [
                "prior travel commitments",
                "scheduling conflict with quarterly review",
                "personal leave"
            ]
            reason = self.rng.choice(reasons)
            return CallResponse(
                provider_call_id=call_id,
                status=CallAttemptStatus.COMPLETED,
                rsvp_outcome=RSVPStatus.DECLINED,
                duration_seconds=duration,
                transcript_summary=(
                    f"AI Voice Agent connected with {request.name}. Invitee declined the invitation "
                    f"for {request.event_name} due to {reason}."
                ),
                is_success=True
            )

        elif roll < 0.75:
            # 3. UNDECIDED (5%)
            duration = self.rng.randint(45, 110)
            return CallResponse(
                provider_call_id=call_id,
                status=CallAttemptStatus.COMPLETED,
                rsvp_outcome=RSVPStatus.UNDECIDED,
                duration_seconds=duration,
                transcript_summary=(
                    f"AI Voice Agent spoke with {request.name}. Invitee is undecided regarding "
                    f"{request.event_name} and requested a follow-up closer to the event date."
                ),
                is_success=True
            )

        elif roll < 0.95:
            # 4. UNREACHABLE / NOT YET CONTACTED (20% -> RSVP remains PENDING)
            duration = self.rng.randint(10, 25)
            scenarios = [
                ("NO_ANSWER", "Line rang 6 times without response; call disconnected."),
                ("BUSY", "Subscriber line was busy; call routed to busy tone."),
                ("VOICEMAIL", "Reached personal voicemail; automated reminder greeting left.")
            ]
            code, reason = self.rng.choice(scenarios)
            return CallResponse(
                provider_call_id=call_id,
                status=CallAttemptStatus.COMPLETED,
                rsvp_outcome=RSVPStatus.PENDING,
                duration_seconds=duration,
                error_code=code,
                error_message=reason,
                transcript_summary=f"Call attempted to {request.phone}. {reason}",
                is_success=True
            )

        else:
            # 5. TECHNICAL FAILURE / IMPERFECT PROVIDER (5% -> FAILED)
            duration = self.rng.randint(3, 12)
            error_scenarios = [
                ("NETWORK_TIMEOUT", "Telephony carrier SIP gateway timed out during media negotiation."),
                ("CALL_DROP", "Unexpected TCP reset from carrier signaling server after 5 seconds."),
                ("CODEC_MISMATCH", "Audio stream negotiation error with regional telecommunications exchange.")
            ]
            err_code, err_msg = self.rng.choice(error_scenarios)
            return CallResponse(
                provider_call_id=call_id,
                status=CallAttemptStatus.FAILED,
                rsvp_outcome='FAILED',
                duration_seconds=duration,
                error_code=err_code,
                error_message=err_msg,
                transcript_summary=f"Call failed: {err_msg}",
                is_success=False
            )
