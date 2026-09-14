import io
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from apps.invitees.models import Invitee

class InviteeImportTests(TestCase):
    """
    Automated test suite for Phase 4: Invitee Import & CSV Engine.
    Covers Happy Path, Preview Mode, Edge Cases, Boundary Values, and Security.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='event_mgr', password='Password123!')
        self.client.force_authenticate(user=self.user)

        self.valid_csv_content = (
            "id,name,phone,email\n"
            "1,Rahul Sharma,+919876543210,rahul@example.com\n"
            "2,Priya Shah,+9198123456789,priya@example.com\n"
            "3,Amit Patel,+919999999999,amit@example.com\n"
        )

    def _create_csv_file(self, content: str, filename: str = 'invitees.csv') -> SimpleUploadedFile:
        return SimpleUploadedFile(filename, content.encode('utf-8'), content_type='text/csv')

    # ==========================================
    # 1. HAPPY PATH & PREVIEW TESTS
    # ==========================================

    def test_preview_mode_does_not_commit_to_database(self):
        """Happy Path: Preview mode validates all rows without inserting into DB."""
        csv_file = self._create_csv_file(self.valid_csv_content)
        res = self.client.post('/api/invitees/import/?preview_only=true', {'file': csv_file}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total_rows'], 3)
        self.assertEqual(res.data['valid_count'], 3)
        self.assertEqual(res.data['invalid_count'], 0)
        self.assertEqual(res.data['imported_count'], 0)
        self.assertTrue(res.data['is_preview'])
        self.assertEqual(len(res.data['sample_valid']), 3)

        # Confirm 0 records in DB
        self.assertEqual(Invitee.objects.count(), 0)

    def test_commit_mode_persists_valid_invitees(self):
        """Happy Path: Commit mode persists valid invitees in MySQL."""
        csv_file = self._create_csv_file(self.valid_csv_content)
        res = self.client.post('/api/invitees/import/', {'file': csv_file, 'preview_only': False}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total_rows'], 3)
        self.assertEqual(res.data['imported_count'], 3)
        self.assertEqual(res.data['invalid_count'], 0)

        # Confirm 3 records in DB with expected data
        self.assertEqual(Invitee.objects.count(), 3)
        rahul = Invitee.objects.get(name='Rahul Sharma')
        self.assertEqual(rahul.phone, '+919876543210')
        self.assertEqual(rahul.email, 'rahul@example.com')
        self.assertEqual(rahul.external_id, '1')

    def test_invitee_list_and_search(self):
        """Happy Path: GET /api/invitees/ returns paginated list and filters by search query."""
        Invitee.objects.create(name='Rahul Sharma', phone='+919876543210', email='rahul@example.com')
        Invitee.objects.create(name='Priya Shah', phone='+9198123456789', email='priya@example.com')

        # List all
        res = self.client.get('/api/invitees/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 2)

        # Search for Rahul
        search_res = self.client.get('/api/invitees/?search=Rahul')
        self.assertEqual(search_res.status_code, status.HTTP_200_OK)
        self.assertEqual(search_res.data['count'], 1)
        self.assertEqual(search_res.data['results'][0]['name'], 'Rahul Sharma')
        self.assertIn('phone_masked', search_res.data['results'][0])

    # ==========================================
    # 2. EDGE CASE TESTS
    # ==========================================

    def test_unauthenticated_request_rejected(self):
        """Edge Case: Unauthenticated import request returns 401."""
        self.client.force_authenticate(user=None)
        csv_file = self._create_csv_file(self.valid_csv_content)
        res = self.client.post('/api/invitees/import/', {'file': csv_file}, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_required_headers_rejected(self):
        """Edge Case: CSV without 'phone' header is rejected with 400 and clear message."""
        bad_csv = "id,name,email\n1,Rahul,rahul@example.com\n"
        csv_file = self._create_csv_file(bad_csv)
        res = self.client.post('/api/invitees/import/', {'file': csv_file}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing required CSV column headers', str(res.data))

    def test_empty_csv_file_rejected(self):
        """Edge Case: Empty file returns 400."""
        csv_file = self._create_csv_file('')
        res = self.client.post('/api/invitees/import/', {'file': csv_file}, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_csv_file_rejected(self):
        """Edge Case: Uploading a .pdf or .exe is rejected."""
        fake_pdf = SimpleUploadedFile('document.pdf', b'%PDF-1.4 dummy', content_type='application/pdf')
        res = self.client.post('/api/invitees/import/', {'file': fake_pdf}, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Only .csv files are supported', str(res.data))

    def test_partial_valid_and_invalid_rows_reported(self):
        """Edge Case: Invalid rows are reported with row numbers and exact reasons; valid rows are saved."""
        mixed_csv = (
            "id,name,phone,email\n"
            "1,Valid User,+919876543210,valid@example.com\n"
            "2,,+9198123456789,missing_name@example.com\n"
            "3,Bad Phone,letters_not_digits,bad_phone@example.com\n"
            "4,Bad Email,+919999999999,not-an-email\n"
            "5,Duplicate User,+919876543210,dup@example.com\n"
        )
        csv_file = self._create_csv_file(mixed_csv)
        res = self.client.post('/api/invitees/import/', {'file': csv_file, 'preview_only': False}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total_rows'], 5)
        self.assertEqual(res.data['valid_count'], 1)
        self.assertEqual(res.data['invalid_count'], 4)
        self.assertEqual(res.data['imported_count'], 1)
        self.assertEqual(len(res.data['errors']), 4)

        # Check error report structure
        error_rows = [err['row'] for err in res.data['errors']]
        self.assertEqual(error_rows, [3, 4, 5, 6])  # Rows 3, 4, 5, 6 corresponding to line numbers in CSV

    # ==========================================
    # 3. BOUNDARY VALUE & NORMALIZATION TESTS
    # ==========================================

    def test_phone_normalization_boundary(self):
        """Boundary: Phone numbers with spaces, hyphens, and brackets are normalized."""
        formatted_csv = (
            "id,name,phone,email\n"
            "1,User One,+91 98765-43210,one@example.com\n"
            "2,User Two,(987) 654-3210,two@example.com\n"
        )
        csv_file = self._create_csv_file(formatted_csv)
        res = self.client.post('/api/invitees/import/', {'file': csv_file, 'preview_only': False}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['imported_count'], 2)
        u1 = Invitee.objects.get(name='User One')
        self.assertEqual(u1.phone, '+919876543210')
        u2 = Invitee.objects.get(name='User Two')
        self.assertEqual(u2.phone, '9876543210')

    # ==========================================
    # 4. SECURITY ATTACK TESTS
    # ==========================================

    def test_csv_formula_injection_sanitization(self):
        """Security: Leading formula symbols (=, +, -, @) are sanitized with prepended single quote."""
        formula_csv = (
            "id,name,phone,email\n"
            "1,=SUM(1+2),+919876543210,formula@example.com\n"
        )
        csv_file = self._create_csv_file(formula_csv)
        res = self.client.post('/api/invitees/import/', {'file': csv_file, 'preview_only': False}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['imported_count'], 1)
        saved = Invitee.objects.get(phone='+919876543210')
        self.assertTrue(saved.name.startswith("'="))
