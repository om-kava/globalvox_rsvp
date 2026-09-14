from django.urls import path
from .views import (
    CampaignListCreateView,
    CampaignDetailView,
    CampaignInviteeListView,
    CampaignStartView,
    CampaignInviteeDetailView,
    CampaignResetView,
    CampaignEnrollView
)

app_name = 'campaigns'

urlpatterns = [
    path('', CampaignListCreateView.as_view(), name='list_create'),
    path('<int:pk>/', CampaignDetailView.as_view(), name='detail'),
    path('<int:pk>/start/', CampaignStartView.as_view(), name='start'),
    path('<int:pk>/reset/', CampaignResetView.as_view(), name='reset'),
    path('<int:pk>/enroll/', CampaignEnrollView.as_view(), name='enroll'),
    path('<int:campaign_id>/invitees/', CampaignInviteeListView.as_view(), name='invitees'),
    path('<int:campaign_id>/invitees/<int:invitee_id>/', CampaignInviteeDetailView.as_view(), name='invitee_detail'),
]
