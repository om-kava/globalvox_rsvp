from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

class AuthenticationTests(TestCase):
    """
    Exhaustive test suite for Phase 3 Authentication & Authorization.
    Covers Happy Path, Edge Cases, Boundary Values, and Security attacks.
    """

    def setUp(self):
        self.client = APIClient()
        self.username = 'test_manager'
        self.password = 'SuperSecurePass2026!'
        self.user = User.objects.create_user(
            username=self.username,
            email='manager@test.com',
            password=self.password,
            first_name='Test',
            last_name='Manager'
        )

    # ==========================================
    # 1. HAPPY PATH TESTS
    # ==========================================

    def test_login_success_returns_jwt_and_user_profile(self):
        """Happy Path: Valid credentials return 200, JWT tokens, and user metadata."""
        response = self.client.post('/api/auth/login/', {
            'username': self.username,
            'password': self.password
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], self.username)
        self.assertEqual(response.data['user']['email'], 'manager@test.com')

    def test_authenticated_access_with_jwt_bearer_token(self):
        """Happy Path: User can query /api/auth/me/ using Authorization: Bearer header."""
        login_res = self.client.post('/api/auth/login/', {
            'username': self.username,
            'password': self.password
        }, format='json')
        access_token = login_res.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        res = self.client.get('/api/auth/me/')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['username'], self.username)

    def test_jwt_token_refresh(self):
        """Happy Path: Refresh token successfully returns a new access token."""
        login_res = self.client.post('/api/auth/login/', {
            'username': self.username,
            'password': self.password
        }, format='json')
        refresh_token = login_res.data['refresh']

        ref_res = self.client.post('/api/auth/refresh/', {
            'refresh': refresh_token
        }, format='json')

        self.assertEqual(ref_res.status_code, status.HTTP_200_OK)
        self.assertIn('access', ref_res.data)

    def test_logout_and_blacklist_refresh_token(self):
        """Happy Path: Logout blacklists the refresh token."""
        login_res = self.client.post('/api/auth/login/', {
            'username': self.username,
            'password': self.password
        }, format='json')
        access_token = login_res.data['access']
        refresh_token = login_res.data['refresh']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_res = self.client.post('/api/auth/logout/', {
            'refresh': refresh_token
        }, format='json')
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Attempting to refresh with blacklisted token must fail with 401
        self.client.credentials()  # Clear credentials
        bad_refresh = self.client.post('/api/auth/refresh/', {
            'refresh': refresh_token
        }, format='json')
        self.assertEqual(bad_refresh.status_code, status.HTTP_401_UNAUTHORIZED)

    # ==========================================
    # 2. EDGE CASE TESTS
    # ==========================================

    def test_unauthenticated_access_rejected(self):
        """Edge Case: Accessing /api/auth/me/ without credentials returns 401."""
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_malformed_bearer_token(self):
        """Edge Case: Malformed or gibberish Bearer token returns 401."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer not_a_valid_jwt_token_structure')
        res = self.client.get('/api/auth/me/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_password_rejected(self):
        """Edge Case: Wrong password returns 400 Bad Request with generic error."""
        res = self.client.post('/api/auth/login/', {
            'username': self.username,
            'password': 'IncorrectPassword999!'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid credentials.', str(res.data.get('detail', '')))

    def test_nonexistent_user_rejected(self):
        """Edge Case: Non-existent username returns 400 Bad Request."""
        res = self.client.post('/api/auth/login/', {
            'username': 'non_existent_user_xyz',
            'password': 'SomePassword123'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid credentials.', str(res.data.get('detail', '')))

    def test_inactive_user_rejected(self):
        """Edge Case: Deactivated account cannot log in."""
        self.user.is_active = False
        self.user.save()

        res = self.client.post('/api/auth/login/', {
            'username': self.username,
            'password': self.password
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('User account is inactive.', str(res.data.get('detail', '')))

    # ==========================================
    # 3. BOUNDARY VALUE TESTS
    # ==========================================

    def test_empty_credentials_rejected(self):
        """Boundary: Blank username or blank password returns 400."""
        res = self.client.post('/api/auth/login/', {'username': '', 'password': ''}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_whitespace_only_username_rejected(self):
        """Boundary: Whitespace-only username returns 400."""
        res = self.client.post('/api/auth/login/', {'username': '   ', 'password': 'pass'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_username_trimmed_successfully(self):
        """Boundary: Username with leading/trailing whitespace is trimmed and authenticates."""
        res = self.client.post('/api/auth/login/', {
            'username': f'  {self.username}  ',
            'password': self.password
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_max_length_boundary_password(self):
        """Boundary: Exactly 128 character password boundary works."""
        long_pass = 'A' * 128
        u = User.objects.create_user(username='boundary_user', password=long_pass)
        res = self.client.post('/api/auth/login/', {
            'username': 'boundary_user',
            'password': long_pass
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_password_exceeding_128_chars_rejected(self):
        """Boundary: Password exceeding 128 chars is rejected by validator."""
        too_long = 'A' * 129
        res = self.client.post('/api/auth/login/', {
            'username': self.username,
            'password': too_long
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ==========================================
    # 4. SECURITY ATTACK TESTS
    # ==========================================

    def test_sql_injection_attempt_in_login(self):
        """Security: SQL injection payload does not cause 500 error or bypass auth."""
        sqli_payloads = [
            "' OR '1'='1",
            "admin' --",
            "admin' /*",
            "' UNION SELECT * FROM auth_user --"
        ]
        for payload in sqli_payloads:
            res = self.client.post('/api/auth/login/', {
                'username': payload,
                'password': "' OR '1'='1"
            }, format='json')
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_xss_payload_in_login(self):
        """Security: XSS script payload in username is rejected safely."""
        xss_payload = '<script>alert(document.cookie)</script>'
        res = self.client.post('/api/auth/login/', {
            'username': xss_payload,
            'password': 'AnyPassword123'
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
