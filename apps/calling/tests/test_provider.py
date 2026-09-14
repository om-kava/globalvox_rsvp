from django.test import TestCase
from apps.calling.base import CallingProvider, CallRequest, CallResponse
from apps.calling.mock_provider import MockCallingProvider
from apps.campaigns.models import RSVPStatus
from apps.calling.models import CallAttemptStatus

class CallingProviderTests(TestCase):
    """
    Automated test suite for Phase 6: Calling Provider Subsystem.
    Covers interface contract compliance, deterministic seeding,
    outcome distribution, and failure simulation.
    """

    def setUp(self):
        self.request = CallRequest(
            invitee_id=1,
            name='Rahul Sharma',
            phone='+919876543210',
            campaign_id=1,
            campaign_name='Annual Business Meet — RSVP',
            event_name='GlobalVox Annual Business Meet',
            attempt_number=1
        )

    def test_provider_contract_compliance(self):
        """Verify MockCallingProvider adheres to the CallingProvider abstract contract."""
        provider = MockCallingProvider()
        self.assertIsInstance(provider, CallingProvider)

        response = provider.initiate_call(self.request)
        self.assertIsInstance(response, CallResponse)
        self.assertTrue(response.provider_call_id.startswith('CALL-SIM-'))
        self.assertGreater(response.duration_seconds, 0)
        self.assertIn(response.status, [CallAttemptStatus.COMPLETED, CallAttemptStatus.FAILED])

    def test_deterministic_seeding_reproducibility(self):
        """Verify that identical seeds produce identical simulated outcomes."""
        provider1 = MockCallingProvider(seed=42)
        provider2 = MockCallingProvider(seed=42)

        res1 = provider1.initiate_call(self.request)
        res2 = provider2.initiate_call(self.request)

        self.assertEqual(res1.status, res2.status)
        self.assertEqual(res1.rsvp_outcome, res2.rsvp_outcome)
        self.assertEqual(res1.duration_seconds, res2.duration_seconds)

    def test_outcome_variety_over_batch(self):
        """Verify that running a batch of 200 calls produces all 5 expected outcomes."""
        provider = MockCallingProvider(seed=12345)
        outcomes = set()
        statuses = set()

        for i in range(200):
            req = CallRequest(
                invitee_id=i,
                name=f'Invitee {i}',
                phone=f'+919876500{i:03d}',
                campaign_id=1,
                campaign_name='Test',
                event_name='Event'
            )
            res = provider.initiate_call(req)
            outcomes.add(res.rsvp_outcome)
            statuses.add(res.status)

        # Confirm all 5 outcomes from the PDF appear in the distribution:
        # Confirmed, Declined, Undecided, Pending (No answer), Failed
        self.assertIn(RSVPStatus.CONFIRMED, outcomes)
        self.assertIn(RSVPStatus.DECLINED, outcomes)
        self.assertIn(RSVPStatus.UNDECIDED, outcomes)
        self.assertIn(RSVPStatus.PENDING, outcomes)
        self.assertIn('FAILED', outcomes)
        self.assertIn(CallAttemptStatus.COMPLETED, statuses)
        self.assertIn(CallAttemptStatus.FAILED, statuses)

    def test_failure_simulation_includes_error_codes(self):
        """Verify that simulated failures contain informative error metadata."""
        provider = MockCallingProvider(seed=999)
        # Search for a failed attempt
        failed_res = None
        for _ in range(50):
            res = provider.initiate_call(self.request)
            if res.status == CallAttemptStatus.FAILED:
                failed_res = res
                break

        if failed_res:
            self.assertFalse(failed_res.is_success)
            self.assertIn(failed_res.error_code, ['NETWORK_TIMEOUT', 'CALL_DROP', 'CODEC_MISMATCH'])
            self.assertTrue(len(failed_res.error_message) > 0)
