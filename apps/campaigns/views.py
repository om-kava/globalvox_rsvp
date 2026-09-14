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

from rest_framework.views import APIView
from apps.campaigns.services.executor import CampaignExecutor, CampaignExecutionConflictError

class CampaignStartView(APIView):
    """
    Initiate campaign execution.
    Enforces atomic database row-locking to prevent concurrent double-starts.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        seed = request.data.get('seed')
        if seed is not None:
            try:
                seed = int(seed)
            except (ValueError, TypeError):
                seed = None

        executor = CampaignExecutor(seed=seed)
        try:
            result = executor.start_campaign(campaign_id=pk)
            return Response(result, status=status.HTTP_200_OK)
        except CampaignExecutionConflictError as err:
            return Response({
                'error': {
                    'code': 'CAMPAIGN_CONFLICT',
                    'message': str(err)
                }
            }, status=status.HTTP_409_CONFLICT)
        except ValueError as err:
            return Response({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': str(err)
                }
            }, status=status.HTTP_404_NOT_FOUND)

from apps.campaigns.serializers import CampaignInviteeDetailSerializer

class CampaignInviteeDetailView(APIView):
    """
    Retrieve full details for an individual invitee within a campaign,
    including masked PII, current RSVP & call status, and complete CallAttempt timeline.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, campaign_id: int, invitee_id: int):
        try:
            ci = CampaignInvitee.objects.select_related('campaign', 'invitee').prefetch_related('call_attempts').get(
                campaign_id=campaign_id,
                invitee_id=invitee_id
            )
        except CampaignInvitee.DoesNotExist:
            return Response({
                'error': {
                    'code': 'NOT_FOUND',
                    'message': f"Invitee with ID {invitee_id} is not enrolled in Campaign {campaign_id}."
                }
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = CampaignInviteeDetailSerializer(ci)
        return Response(serializer.data, status=status.HTTP_200_OK)


