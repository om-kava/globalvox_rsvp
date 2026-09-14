from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CallRequest:
    """
    Standardized payload sent to an AI Voice Calling Provider.
    """
    invitee_id: int
    name: str
    phone: str
    campaign_id: int
    campaign_name: str
    event_name: str
    attempt_number: int = 1

@dataclass
class CallResponse:
    """
    Standardized response returned by an AI Voice Calling Provider.
    """
    provider_call_id: str
    status: str                         # COMPLETED | FAILED
    rsvp_outcome: str                   # CONFIRMED | DECLINED | UNDECIDED | FAILED | PENDING
    duration_seconds: int = 0
    error_code: str = ''                # Machine-readable error code if failed
    error_message: str = ''             # Detailed error explanation
    transcript_summary: str = ''        # Summary of conversation between AI agent and invitee
    is_success: bool = True

class CallingProvider(ABC):
    """
    Abstract Base Class defining the contract for AI Voice Calling services.
    Any telephony or conversational voice AI provider (e.g. Retell, Twilio, Vapi,
    or GlobalVox Voice) must implement this interface.
    """

    @abstractmethod
    def initiate_call(self, request: CallRequest) -> CallResponse:
        """
        Dispatches a phone call to the invitee and determines the RSVP outcome.
        """
        pass
