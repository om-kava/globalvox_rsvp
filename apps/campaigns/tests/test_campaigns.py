from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from apps.campaigns.models import Campaign, CampaignInvitee, CampaignStatus, RSVPStatus, CallStatus
from apps.invitees.models import Invitee

class CampaignManagementTests(TestCase):
    """
    Automated test suite for Phase 5: Campaign Management.
    Covers Happy Path, Listing, Details with Metrics, Invitee Filtering, and Edge Cases.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='event_lead', password='Password123!')
        self.client.force_authenticate(user=self.user)

        # Pre-seed invitees
        self.inv1 = Invitee.objects.create(name='Rahul Sharma', phone='+919876543210', email='rahul@example.com')
        self.inv2 = Invitee.objects.create(name='Priya Shah', phone='+9198123456789', email='priya@example.com')
        self.inv3 = Invitee.objects.create(name='Amit Patel', phone='+919999999999', email='amit@example.com')

    # ==========================================
    # 1. HAPPY PATH TESTS
    # ==========================================

    def test_create_campaign_with_specific_invitees(self):
        """Happy Path: Create campaign from PDF specification and enroll invitees."""
        payload = {
            'name': 'Annual Business Meet — RSVP',
            'event_name': 'GlobalVox Annual Business Meet',
            'event_date': '2026-10-25',
            'event_location': 'Ahmedabad',
            'objective': 'AI agent should contact each invitee and determine attendance.',
            'invitee_ids': [self.inv1.id, self.inv2.id]
        }
        res = self.client.post('/api/campaigns/', payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['name'], 'Annual Business Meet — RSVP')
        self.assertEqual(res.data['event_name'], 'GlobalVox Annual Business Meet')
        self.assertEqual(res.data['event_date'], '2026-10-25')
        self.assertEqual(res.data['event_location'], 'Ahmedabad')
        self.assertEqual(res.data['status'], CampaignStatus.DRAFT)

        # Confirm metrics in response
        metrics = res.data['metrics']
        self.assertEqual(metrics['total_invitees'], 2)
        self.assertEqual(metrics['pending'], 2)
        self.assertEqual(metrics['confirmed'], 0)

        # Confirm DB state
        campaign = Campaign.objects.get(id=res.data['id'])
        self.assertEqual(campaign.created_by, self.user)
        self.assertEqual(campaign.campaign_invitees.count(), 2)

    def test_create_campaign_enrolling_all_invitees(self):
        """Happy Path: Option enroll_all_invitees=True links all invitees in DB."""
        payload = {
            'name': 'All Hands Campaign',
            'event_name': 'GlobalVox Summit',
            'event_date': '2026-11-15',
            'event_location': 'Ahmedabad',
            'enroll_all_invitees': True
        }
        res = self.client.post('/api/campaigns/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['metrics']['total_invitees'], 3)

    def test_list_campaigns(self):
        """Happy Path: GET /api/campaigns/ returns summary list of campaigns."""
        camp = Campaign.objects.create(
            name='Test Campaign',
            event_name='Test Event',
            event_date='2026-10-25',
            event_location='Ahmedabad'
        )
        CampaignInvitee.objects.create(campaign=camp, invitee=self.inv1)

        res = self.client.get('/api/campaigns/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data['results']), 1)
        first = res.data['results'][0]
        self.assertIn('total_invitees', first)
        self.assertEqual(first['total_invitees'], 1)

    def test_retrieve_campaign_detail_with_live_metrics(self):
        """Happy Path: GET /api/campaigns/<id>/ includes accurate metrics dictionary."""
        camp = Campaign.objects.create(
            name='Metric Test Campaign',
            event_name='Annual Meet',
            event_date='2026-10-25',
            event_location='Ahmedabad'
        )
        CampaignInvitee.objects.create(campaign=camp, invitee=self.inv1, rsvp_status=RSVPStatus.CONFIRMED, call_status=CallStatus.COMPLETED)
        CampaignInvitee.objects.create(campaign=camp, invitee=self.inv2, rsvp_status=RSVPStatus.DECLINED, call_status=CallStatus.COMPLETED)
        CampaignInvitee.objects.create(campaign=camp, invitee=self.inv3, rsvp_status=RSVPStatus.PENDING, call_status=CallStatus.NOT_ATTEMPTED)

        res = self.client.get(f'/api/campaigns/{camp.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        metrics = res.data['metrics']
        self.assertEqual(metrics['total_invitees'], 3)
        self.assertEqual(metrics['confirmed'], 1)
        self.assertEqual(metrics['declined'], 1)
        self.assertEqual(metrics['pending'], 1)

    def test_list_campaign_invitees_with_filters(self):
        """Happy Path: GET /api/campaigns/<id>/invitees/ filters by status and search."""
        camp = Campaign.objects.create(
            name='Invitees List Test',
            event_name='Meet',
            event_date='2026-10-25',
            event_location='Ahmedabad'
        )
        CampaignInvitee.objects.create(campaign=camp, invitee=self.inv1, rsvp_status=RSVPStatus.CONFIRMED)
        CampaignInvitee.objects.create(campaign=camp, invitee=self.inv2, rsvp_status=RSVPStatus.DECLINED)

        # Filter by rsvp_status=CONFIRMED
        res = self.client.get(f'/api/campaigns/{camp.id}/invitees/?rsvp_status=CONFIRMED')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['name'], 'Rahul Sharma')
        self.assertEqual(res.data['results'][0]['rsvp_status'], 'CONFIRMED')
        self.assertIn('phone_masked', res.data['results'][0])

        # Search by name query
        search_res = self.client.get(f'/api/campaigns/{camp.id}/invitees/?search=Priya')
        self.assertEqual(search_res.status_code, status.HTTP_200_OK)
        self.assertEqual(search_res.data['count'], 1)
        self.assertEqual(search_res.data['results'][0]['name'], 'Priya Shah')

    # ==========================================
    # 2. EDGE CASE TESTS
    # ==========================================

    def test_unauthenticated_requests_rejected(self):
        """Edge Case: Unauthenticated requests return 401."""
        self.client.force_authenticate(user=None)
        res = self.client.get('/api/campaigns/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_campaign_missing_fields_rejected(self):
        """Edge Case: Missing required metadata rejected with 400."""
        res = self.client.post('/api/campaigns/', {'name': 'Incomplete'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('event_name', res.data)
        self.assertIn('event_date', res.data)
        self.assertIn('event_location', res.data)

    def test_create_campaign_invalid_date_format(self):
        """Edge Case: Malformed date string rejected with 400."""
        payload = {
            'name': 'Date Test',
            'event_name': 'Event',
            'event_date': 'invalid-date-string',
            'event_location': 'Ahmedabad'
        }
        res = self.client.post('/api/campaigns/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('event_date', res.data)

    def test_nonexistent_campaign_returns_404(self):
        """Edge Case: Nonexistent campaign ID returns 404."""
        res = self.client.get('/api/campaigns/99999/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        invitees_res = self.client.get('/api/campaigns/99999/invitees/')
        self.assertEqual(invitees_res.status_code, status.HTTP_404_NOT_FOUND)
