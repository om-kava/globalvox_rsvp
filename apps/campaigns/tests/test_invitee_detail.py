from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from apps.campaigns.models import Campaign, CampaignInvitee, CampaignStatus, RSVPStatus, CallStatus
from apps.calling.models import CallAttempt, CallAttemptStatus
from apps.invitees.models import Invitee

class IndividualInviteeDetailTests(TestCase):
    """
    Automated test suite for Phase 9: Individual Invitee View & Call History Timeline.
    Verifies Section 5 of the assessment PDF (Name, Masked Phone, Campaign, Status, Call history).
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='detail_mgr', password='Password123!')
        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create(
            name='Annual Business Meet — RSVP',
            event_name='GlobalVox Annual Business Meet',
            event_date='2026-10-25',
            event_location='Ahmedabad',
            status=CampaignStatus.COMPLETED
        )

        self.invitee = Invitee.objects.create(
            name='Rahul Sharma',
            phone='+919876543210',
            email='rahul@example.com',
            external_id='1'
        )

        self.ci = CampaignInvitee.objects.create(
            campaign=self.campaign,
            invitee=self.invitee,
            rsvp_status=RSVPStatus.CONFIRMED,
            call_status=CallStatus.COMPLETED,
            attempt_count=2,
            notes='Final call confirmed attendance for 1 guest.'
        )

        # Attempt 1: Unreachable
        CallAttempt.objects.create(
            campaign_invitee=self.ci,
            attempt_number=1,
            provider_call_id='CALL-SIM-ATTEMPT1',
            status=CallAttemptStatus.COMPLETED,
            rsvp_outcome=RSVPStatus.PENDING,
            duration_seconds=15,
            error_code='NO_ANSWER',
            error_message='Line rang with no answer.',
            transcript_summary='Attempt 1: No answer from recipient.'
        )

        # Attempt 2: Connected & Confirmed
        CallAttempt.objects.create(
            campaign_invitee=self.ci,
            attempt_number=2,
            provider_call_id='CALL-SIM-ATTEMPT2',
            status=CallAttemptStatus.COMPLETED,
            rsvp_outcome=RSVPStatus.CONFIRMED,
            duration_seconds=48,
            transcript_summary='Attempt 2: AI Voice Agent confirmed attendance with Rahul Sharma.'
        )

    # ==========================================
    # 1. HAPPY PATH TESTS
    # ==========================================

    def test_retrieve_individual_invitee_detail_with_timeline(self):
        """Happy Path: Matches Section 5 specification (Name, Masked Phone, Campaign, Status, Call, Attempts)."""
        url = f'/api/campaigns/{self.campaign.id}/invitees/{self.invitee.id}/'
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Check invitee data & phone privacy masking
        inv_data = res.data['invitee']
        self.assertEqual(inv_data['name'], 'Rahul Sharma')
        self.assertEqual(inv_data['phone_masked'], '+919876 ****10')
        self.assertEqual(inv_data['email'], 'rahul@example.com')

        # Check campaign metadata
        camp_data = res.data['campaign']
        self.assertEqual(camp_data['name'], 'Annual Business Meet — RSVP')
        self.assertEqual(camp_data['event_name'], 'GlobalVox Annual Business Meet')

        # Check status
        self.assertEqual(res.data['rsvp_status'], RSVPStatus.CONFIRMED)
        self.assertEqual(res.data['call_status'], CallStatus.COMPLETED)
        self.assertEqual(res.data['attempt_count'], 2)

        # Check chronological CallAttempt audit timeline
        attempts = res.data['attempts']
        self.assertEqual(len(attempts), 2)
        # Verify attempt properties
        att2 = attempts[0]  # Most recent
        self.assertEqual(att2['attempt_number'], 2)
        self.assertEqual(att2['provider_call_id'], 'CALL-SIM-ATTEMPT2')
        self.assertEqual(att2['duration_seconds'], 48)
        self.assertIn('confirmed attendance', att2['transcript_summary'])

    # ==========================================
    # 2. EDGE CASE TESTS
    # ==========================================

    def test_invitee_not_enrolled_in_campaign_returns_404(self):
        """Edge Case: Querying an invitee who is not part of this campaign returns 404."""
        other_inv = Invitee.objects.create(name='Other Person', phone='+919876599999', email='other@example.com')
        url = f'/api/campaigns/{self.campaign.id}/invitees/{other_inv.id}/'
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('NOT_FOUND', str(res.data))

    def test_nonexistent_campaign_returns_404(self):
        """Edge Case: Nonexistent campaign returns 404."""
        res = self.client.get(f'/api/campaigns/99999/invitees/{self.invitee.id}/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_rejected(self):
        """Edge Case: Unauthenticated request returns 401."""
        self.client.force_authenticate(user=None)
        res = self.client.get(f'/api/campaigns/{self.campaign.id}/invitees/{self.invitee.id}/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
