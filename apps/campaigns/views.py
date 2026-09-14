from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from django.db.models import Q

from apps.campaigns.models import Campaign, CampaignInvitee
from apps.campaigns.serializers import (
    CampaignListSerializer,
    CampaignDetailSerializer,
    CampaignCreateSerializer,
    CampaignInviteeSerializer
)

class CampaignListCreateView(generics.ListCreateAPIView):
    """
    List all campaigns or create a new RSVP calling campaign.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CampaignCreateSerializer
        return CampaignListSerializer

    def get_queryset(self):
        return Campaign.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = serializer.save(created_by=request.user)

        # Return full detail response including initial metrics
        detail_serializer = CampaignDetailSerializer(campaign)
        headers = self.get_success_headers(detail_serializer.data)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class CampaignDetailView(generics.RetrieveAPIView):
    """
    Retrieve single campaign details along with real-time aggregated metrics.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CampaignDetailSerializer
    queryset = Campaign.objects.all()

class CampaignInviteeListView(generics.ListAPIView):
    """
    List invitees enrolled in a specific campaign.
    Supports filtering by ?rsvp_status=..., ?call_status=..., and ?search=...
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CampaignInviteeSerializer

    def get_queryset(self):
        campaign_id = self.kwargs.get('campaign_id')
        try:
            campaign = Campaign.objects.get(id=campaign_id)
        except Campaign.DoesNotExist:
            raise NotFound(f"Campaign with ID {campaign_id} does not exist.")

        queryset = campaign.campaign_invitees.select_related('invitee').order_by('id')

        rsvp_status = self.request.query_params.get('rsvp_status')
        if rsvp_status:
            queryset = queryset.filter(rsvp_status=rsvp_status.upper())

        call_status = self.request.query_params.get('call_status')
        if call_status:
            queryset = queryset.filter(call_status=call_status.upper())

        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(invitee__name__icontains=search) |
                Q(invitee__phone__icontains=search) |
                Q(invitee__email__icontains=search)
            )

        return queryset
