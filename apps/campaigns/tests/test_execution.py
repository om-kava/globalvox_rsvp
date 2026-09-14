from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from apps.campaigns.models import Campaign, CampaignInvitee, CampaignStatus, RSVPStatus, CallStatus
from apps.calling.models import CallAttempt, CallAttemptStatus
from apps.calling.base import CallingProvider, CallRequest, CallResponse
from apps.calling.mock_provider import MockCallingProvider
from apps.invitees.models import Invitee

class FlakyTestProvider(CallingProvider):
    """
    Test provider that forces a failure on a specific invitee to verify failure resilience.
    """
    def initiate_call(self, request: CallRequest) -> CallResponse:
        if 'Fail' in request.name:
            return CallResponse(
                provider_call_id='FAIL-ERR-1',
                status=CallAttemptStatus.FAILED,
                rsvp_outcome='FAILED',
                duration_seconds=5,
                error_code='NETWORK_TIMEOUT',
                error_message='Forced carrier timeout simulation',
                transcript_summary='Call dropped during setup.',
                is_success=False
            )
        return CallResponse(
            provider_call_id='SUCCESS-1',
            status=CallAttemptStatus.COMPLETED,
            rsvp_outcome=RSVPStatus.CONFIRMED,
            duration_seconds=45,
            transcript_summary='Invitee confirmed attendance.',
            is_success=True
        )

class CampaignExecutionTests(TestCase):
    """
    Automated test suite for Phase 7: Campaign Execution Engine.
    Covers Happy Path execution, concurrency locking, double-start defense,
    audit trail creation, and failure tolerance.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='exec_mgr', password='Password123!')
        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(
            name='Execution Test Campaign',
            event_name='Annual Business Meet',
            event_date='2026-10-25',
            event_location='Ahmedabad',
            status=CampaignStatus.DRAFT
        )

        self.inv1 = Invitee.objects.create(name='Rahul Sharma', phone='+919876543210', email='rahul@example.com')
        self.inv2 = Invitee.objects.create(name='Priya Shah', phone='+9198123456789', email='priya@example.com')
        self.inv3 = Invitee.objects.create(name='Amit Patel', phone='+919999999999', email='amit@example.com')

        self.ci1 = CampaignInvitee.objects.create(campaign=self.campaign, invitee=self.inv1)
        self.ci2 = CampaignInvitee.objects.create(campaign=self.campaign, invitee=self.inv2)
        self.ci3 = CampaignInvitee.objects.create(campaign=self.campaign, invitee=self.inv3)

    # ==========================================
    # 1. HAPPY PATH TESTS
    # ==========================================

    def test_start_campaign_end_to_end(self):
        """Happy Path: Starting campaign executes calls, creates CallAttempts, and transitions to COMPLETED."""
        res = self.client.post(f'/api/campaigns/{self.campaign.id}/start/', {'seed': 42}, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], CampaignStatus.COMPLETED)
        self.assertEqual(res.data['calls_dispatched'], 3)
        self.assertIsNotNone(res.data['started_at'])
        self.assertIsNotNone(res.data['completed_at'])

        # Verify DB state
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CampaignStatus.COMPLETED)

        # Verify CallAttempts logged
        attempts = CallAttempt.objects.filter(campaign_invitee__campaign=self.campaign)
        self.assertEqual(attempts.count(), 3)
        for att in attempts:
            self.assertTrue(att.provider_call_id.startswith('CALL-SIM-'))
            self.assertGreater(att.duration_seconds, 0)
            self.assertTrue(len(att.transcript_summary) > 0)

        # Verify CampaignInvitee records updated
        for ci in [self.ci1, self.ci2, self.ci3]:
            ci.refresh_from_db()
            self.assertEqual(ci.attempt_count, 1)
            self.assertIsNotNone(ci.last_attempt_at)
            self.assertNotEqual(ci.call_status, CallStatus.NOT_ATTEMPTED)

        # Verify metrics consistency
        metrics = self.campaign.calculate_metrics()
        self.assertEqual(metrics['total_invitees'], 3)
        total_accounted = (
            metrics['confirmed'] +
            metrics['declined'] +
            metrics['undecided'] +
            metrics['pending'] +
            metrics['failed']
        )
        self.assertEqual(total_accounted, 3)

    # ==========================================
    # 2. CONCURRENCY & DOUBLE-START DEFENSE
    # ==========================================

    def test_duplicate_start_prevented_with_409_conflict(self):
        """Concurrency: A campaign that has already been started or completed cannot be started again."""
        # 1st start
        first_res = self.client.post(f'/api/campaigns/{self.campaign.id}/start/', format='json')
        self.assertEqual(first_res.status_code, status.HTTP_200_OK)

        # 2nd start attempt must be rejected with 409 Conflict
        second_res = self.client.post(f'/api/campaigns/{self.campaign.id}/start/', format='json')
        self.assertEqual(second_res.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('CAMPAIGN_CONFLICT', str(second_res.data))

    # ==========================================
    # 3. FAILURE RESILIENCE TESTS
    # ==========================================

    def test_partial_carrier_failure_does_not_halt_campaign(self):
        """Resilience: If one invitee call fails, it is recorded as FAILED and campaign finishes remaining calls."""
        # Create an invitee destined to fail
        fail_inv = Invitee.objects.create(name='Fail Person', phone='+919876500999', email='fail@example.com')
        fail_ci = CampaignInvitee.objects.create(campaign=self.campaign, invitee=fail_inv)

        from apps.campaigns.services.executor import CampaignExecutor
        executor = CampaignExecutor(provider=FlakyTestProvider())
        result = executor.start_campaign(campaign_id=self.campaign.id)

        self.assertEqual(result['status'], CampaignStatus.COMPLETED)
        self.assertEqual(result['calls_dispatched'], 4)
        self.assertEqual(result['failed_calls'], 1)
        self.assertEqual(result['successful_calls'], 3)

        # Verify failed invitee state
        fail_ci.refresh_from_db()
        self.assertEqual(fail_ci.call_status, CallStatus.FAILED)
        self.assertEqual(fail_ci.rsvp_status, RSVPStatus.PENDING)

        # Verify CallAttempt record contains error metadata
        fail_attempt = CallAttempt.objects.get(campaign_invitee=fail_ci)
        self.assertEqual(fail_attempt.status, CallAttemptStatus.FAILED)
        self.assertEqual(fail_attempt.error_code, 'NETWORK_TIMEOUT')
        self.assertIn('timeout', fail_attempt.error_message)

    # ==========================================
    # 4. EDGE CASE TESTS
    # ==========================================

    def test_start_nonexistent_campaign_returns_404(self):
        """Edge Case: Calling start on nonexistent ID returns 404."""
        res = self.client.post('/api/campaigns/99999/start/', format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_start_request_rejected(self):
        """Edge Case: Unauthenticated start returns 401."""
        self.client.force_authenticate(user=None)
        res = self.client.post(f'/api/campaigns/{self.campaign.id}/start/', format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
