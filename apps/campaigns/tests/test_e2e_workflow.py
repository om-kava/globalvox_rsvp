import io
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status

from apps.campaigns.models import Campaign, CampaignInvitee, CampaignStatus, RSVPStatus, CallStatus
from apps.calling.models import CallAttempt
from apps.invitees.models import Invitee

class EndToEndBusinessWorkflowTests(TestCase):
    """
    Comprehensive End-to-End Integration Suite simulating the complete user lifecycle:
    Login -> CSV Preview -> CSV Import -> Campaign Create -> Start Calls ->
    Metrics Aggregation -> Filter/Search -> Invitee Inspection -> Concurrency Rejection -> Logout.
    """

    def setUp(self):
        self.client = APIClient()
        self.username = 'event_director'
        self.password = 'EnterprisePass2026!'
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email='director@globalvox.com'
        )

        self.sample_csv_content = (
            "id,name,phone,email\n"
            "1,Rahul Sharma,+919876543210,rahul@example.com\n"
            "2,Priya Shah,+9198123456789,priya@example.com\n"
            "3,Amit Patel,+919999999999,amit@example.com\n"
            "4,Sneha Joshi,+919876500001,sneha@example.com\n"
            "5,Rajesh Kumar,+919876500002,rajesh@example.com\n"
        )

    def test_complete_end_to_end_business_lifecycle(self):
        """
        Executes the entire assessment workflow sequentially using REST API requests.
        """

        # ----------------------------------------------------------------------
        # STEP 1: Authenticate with JWT
        # ----------------------------------------------------------------------
        login_res = self.client.post('/api/auth/login/', {
            'username': self.username,
            'password': self.password
        }, format='json')
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_res.data)
        access_token = login_res.data['access']
        refresh_token = login_res.data['refresh']

        # Configure APIClient to use Bearer token for all subsequent requests
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Verify /api/auth/me/
        me_res = self.client.get('/api/auth/me/')
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        self.assertEqual(me_res.data['username'], self.username)

        # ----------------------------------------------------------------------
        # STEP 2: Invitee CSV Ingestion (Preview Mode)
        # ----------------------------------------------------------------------
        preview_file = SimpleUploadedFile('invitees.csv', self.sample_csv_content.encode('utf-8'), content_type='text/csv')
        preview_res = self.client.post('/api/invitees/import/?preview_only=true', {'file': preview_file}, format='multipart')
        self.assertEqual(preview_res.status_code, status.HTTP_200_OK)
        self.assertEqual(preview_res.data['total_rows'], 5)
        self.assertEqual(preview_res.data['valid_count'], 5)
        self.assertEqual(preview_res.data['invalid_count'], 0)
        self.assertEqual(preview_res.data['imported_count'], 0)
        self.assertEqual(Invitee.objects.count(), 0)  # Database remains untouched

        # ----------------------------------------------------------------------
        # STEP 3: Invitee CSV Ingestion (Commit Mode)
        # ----------------------------------------------------------------------
        commit_file = SimpleUploadedFile('invitees.csv', self.sample_csv_content.encode('utf-8'), content_type='text/csv')
        commit_res = self.client.post('/api/invitees/import/', {'file': commit_file, 'preview_only': False}, format='multipart')
        self.assertEqual(commit_res.status_code, status.HTTP_200_OK)
        self.assertEqual(commit_res.data['imported_count'], 5)
        self.assertEqual(Invitee.objects.count(), 5)

        # ----------------------------------------------------------------------
        # STEP 4: Create Campaign and Enroll Invitees
        # ----------------------------------------------------------------------
        camp_payload = {
            'name': 'Annual Business Meet — RSVP',
            'event_name': 'GlobalVox Annual Business Meet',
            'event_date': '2026-10-25',
            'event_location': 'Ahmedabad',
            'objective': 'AI voice agent contacts invitees to collect attendance confirmation.',
            'enroll_all_invitees': True
        }
        camp_create_res = self.client.post('/api/campaigns/', camp_payload, format='json')
        self.assertEqual(camp_create_res.status_code, status.HTTP_201_CREATED)
        campaign_id = camp_create_res.data['id']
        self.assertEqual(camp_create_res.data['status'], CampaignStatus.DRAFT)
        self.assertEqual(camp_create_res.data['metrics']['total_invitees'], 5)
        self.assertEqual(camp_create_res.data['metrics']['pending'], 5)

        # ----------------------------------------------------------------------
        # STEP 5: Start the Campaign Calling Process
        # ----------------------------------------------------------------------
        start_res = self.client.post(f'/api/campaigns/{campaign_id}/start/', {'seed': 42}, format='json')
        self.assertEqual(start_res.status_code, status.HTTP_200_OK)
        self.assertEqual(start_res.data['status'], CampaignStatus.COMPLETED)
        self.assertEqual(start_res.data['calls_dispatched'], 5)

        # ----------------------------------------------------------------------
        # STEP 6: Verify Campaign Detail & Live Aggregated Metrics
        # ----------------------------------------------------------------------
        detail_res = self.client.get(f'/api/campaigns/{campaign_id}/')
        self.assertEqual(detail_res.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_res.data['status'], CampaignStatus.COMPLETED)

        metrics = detail_res.data['metrics']
        self.assertEqual(metrics['total_invitees'], 5)
        total_accounted = (
            metrics['confirmed'] +
            metrics['declined'] +
            metrics['undecided'] +
            metrics['pending'] +
            metrics['failed']
        )
        self.assertEqual(total_accounted, 5)

        # ----------------------------------------------------------------------
        # STEP 7: List Enrolled Campaign Invitees & Filter
        # ----------------------------------------------------------------------
        invitees_res = self.client.get(f'/api/campaigns/{campaign_id}/invitees/')
        self.assertEqual(invitees_res.status_code, status.HTTP_200_OK)
        self.assertEqual(invitees_res.data['count'], 5)

        # Check phone masking in results
        first_invitee = invitees_res.data['results'][0]
        self.assertIn('****', first_invitee['phone_masked'])
        self.assertEqual(first_invitee['attempt_count'], 1)

        # Filter by name search
        search_res = self.client.get(f'/api/campaigns/{campaign_id}/invitees/?search=Rahul')
        self.assertEqual(search_res.status_code, status.HTTP_200_OK)
        self.assertEqual(search_res.data['count'], 1)
        self.assertEqual(search_res.data['results'][0]['name'], 'Rahul Sharma')

        # ----------------------------------------------------------------------
        # STEP 8: Inspect Individual Invitee Audit Timeline
        # ----------------------------------------------------------------------
        target_invitee_id = first_invitee['invitee_id']
        inspect_res = self.client.get(f'/api/campaigns/{campaign_id}/invitees/{target_invitee_id}/')
        self.assertEqual(inspect_res.status_code, status.HTTP_200_OK)
        self.assertIn('attempts', inspect_res.data)
        self.assertGreaterEqual(len(inspect_res.data['attempts']), 1)
        att = inspect_res.data['attempts'][0]
        self.assertTrue(att['provider_call_id'].startswith('CALL-SIM-'))
        self.assertGreater(att['duration_seconds'], 0)
        self.assertTrue(len(att['transcript_summary']) > 0)

        # ----------------------------------------------------------------------
        # STEP 9: Verify Concurrency / Double-Start Protection
        # ----------------------------------------------------------------------
        retry_res = self.client.post(f'/api/campaigns/{campaign_id}/start/', format='json')
        self.assertEqual(retry_res.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('CAMPAIGN_CONFLICT', str(retry_res.data))

        # ----------------------------------------------------------------------
        # STEP 10: Logout and Invalidate Refresh Token
        # ----------------------------------------------------------------------
        logout_res = self.client.post('/api/auth/logout/', {'refresh': refresh_token}, format='json')
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Clear client auth and verify refresh token is blacklisted
        self.client.credentials()
        bad_refresh = self.client.post('/api/auth/refresh/', {'refresh': refresh_token}, format='json')
        self.assertEqual(bad_refresh.status_code, status.HTTP_401_UNAUTHORIZED)
