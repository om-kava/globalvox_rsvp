from rest_framework import serializers
from django.db import transaction
from apps.campaigns.models import Campaign, CampaignInvitee, CampaignStatus, RSVPStatus, CallStatus
from apps.invitees.models import Invitee

class CampaignListSerializer(serializers.ModelSerializer):
    """
    Serializer for campaign dashboard cards and tables.
    """
    total_invitees = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'event_name', 'event_date', 'event_location',
            'objective', 'status', 'total_invitees',
            'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = fields

    def get_total_invitees(self, obj) -> int:
        return obj.campaign_invitees.count()

class CampaignDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer including real-time aggregated metrics.
    """
    metrics = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'event_name', 'event_date', 'event_location',
            'objective', 'status', 'metrics',
            'created_at', 'started_at', 'completed_at'
        ]
        read_only_fields = fields

    def get_metrics(self, obj) -> dict:
        return obj.calculate_metrics()

class CampaignCreateSerializer(serializers.ModelSerializer):
    """
    Validates campaign creation and associates invitee records atomically.
    """
    invitee_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text="List of specific Invitee IDs to enroll in this campaign"
    )
    enroll_all_invitees = serializers.BooleanField(
        required=False,
        default=False,
        write_only=True,
        help_text="If true, automatically enrolls all existing invitees in the database"
    )

    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'event_name', 'event_date', 'event_location',
            'objective', 'status', 'invitee_ids', 'enroll_all_invitees'
        ]
        read_only_fields = ['id', 'status']

    def validate_name(self, value):
        val = value.strip()
        if not val:
            raise serializers.ValidationError("Campaign name cannot be blank.")
        return val

    def validate_event_name(self, value):
        val = value.strip()
        if not val:
            raise serializers.ValidationError("Event name cannot be blank.")
        return val

    def validate_event_location(self, value):
        val = value.strip()
        if not val:
            raise serializers.ValidationError("Event location cannot be blank.")
        return val

    def create(self, validated_data):
        invitee_ids = validated_data.pop('invitee_ids', [])
        enroll_all = validated_data.pop('enroll_all_invitees', False)

        with transaction.atomic():
            campaign = Campaign.objects.create(**validated_data)

            # Determine invitees to enroll
            if enroll_all:
                target_invitees = Invitee.objects.all()
            elif invitee_ids:
                target_invitees = Invitee.objects.filter(id__in=invitee_ids)
            else:
                target_invitees = []

            # Bulk create CampaignInvitee records
            participations = [
                CampaignInvitee(
                    campaign=campaign,
                    invitee=invitee,
                    rsvp_status=RSVPStatus.PENDING,
                    call_status=CallStatus.NOT_ATTEMPTED
                )
                for invitee in target_invitees
            ]
            if participations:
                CampaignInvitee.objects.bulk_create(participations, ignore_conflicts=True)

        return campaign

class CampaignInviteeSerializer(serializers.ModelSerializer):
    """
    Serializer for invitees enrolled in a specific campaign.
    """
    name = serializers.CharField(source='invitee.name', read_only=True)
    phone_masked = serializers.CharField(source='invitee.phone_masked', read_only=True)
    email = serializers.EmailField(source='invitee.email', read_only=True)

    class Meta:
        model = CampaignInvitee
        fields = [
            'id', 'campaign_id', 'invitee_id', 'name', 'phone_masked', 'email',
            'rsvp_status', 'call_status', 'attempt_count', 'last_attempt_at',
            'notes', 'updated_at'
        ]
        read_only_fields = fields
