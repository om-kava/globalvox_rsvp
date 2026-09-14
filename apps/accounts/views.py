from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import login as django_login, logout as django_logout

from .serializers import LoginSerializer, UserSerializer, LogoutSerializer

class LoginView(APIView):
    """
    Authenticate business users and issue signed JWT tokens (access + refresh)
    alongside establishing a secure browser session.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']

        # Generate JWT token pair
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Establish Django session for dual-mode browser navigation
        django_login(request, user)

        return Response({
            'message': 'Login successful.',
            'access': access_token,
            'refresh': refresh_token,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)

class CurrentUserView(APIView):
    """
    Returns the authenticated business user's profile.
    Accepts either Bearer JWT or active Session.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class LogoutView(APIView):
    """
    Invalidates session and blacklists supplied JWT refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            refresh_token = serializer.validated_data.get('refresh')
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except (TokenError, Exception):
                    # Proceed even if token is already invalid or expired
                    pass

        django_logout(request)
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)
