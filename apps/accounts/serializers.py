from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer representing authenticated user profile.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
        read_only_fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']

class LoginSerializer(serializers.Serializer):
    """
    Validates login credentials against strict boundary rules and returns authenticated user.
    """
    username = serializers.CharField(
        max_length=150,
        min_length=1,
        trim_whitespace=True,
        required=True,
        error_messages={
            'blank': 'Username cannot be blank.',
            'max_length': 'Username cannot exceed 150 characters.'
        }
    )
    password = serializers.CharField(
        max_length=128,
        min_length=1,
        trim_whitespace=False,
        write_only=True,
        required=True,
        error_messages={
            'blank': 'Password cannot be blank.',
            'max_length': 'Password cannot exceed 128 characters.'
        }
    )

    def validate(self, attrs):
        username = attrs.get('username', '').strip()
        password = attrs.get('password', '')

        if not username:
            raise serializers.ValidationError({'username': 'Username cannot be blank or whitespace only.'})
        if not password:
            raise serializers.ValidationError({'password': 'Password cannot be blank.'})

        # Boundary checks
        if len(username) > 150:
            raise serializers.ValidationError({'username': 'Username boundary exceeded (max 150 characters).'})
        if len(password) > 128:
            raise serializers.ValidationError({'password': 'Password boundary exceeded (max 128 characters).'})

        # Authenticate user
        user = authenticate(username=username, password=password)
        if not user:
            # Check if user exists and password is correct, but account is deactivated
            inactive_user = User.objects.filter(username=username).first()
            if inactive_user and not inactive_user.is_active and inactive_user.check_password(password):
                raise serializers.ValidationError({'detail': 'User account is inactive.'})
            raise serializers.ValidationError({'detail': 'Invalid credentials.'})

        attrs['user'] = user
        return attrs

class LogoutSerializer(serializers.Serializer):
    """
    Serializer for logging out and optionally blacklisting JWT refresh token.
    """
    refresh = serializers.CharField(required=False, allow_blank=True)
