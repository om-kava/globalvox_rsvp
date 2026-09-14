from django.urls import path
from .views import CampaignListCreateView, CampaignDetailView, CampaignInviteeListView, CampaignStartView

app_name = 'campaigns'

urlpatterns = [
    path('', CampaignListCreateView.as_view(), name='list_create'),
    path('<int:pk>/', CampaignDetailView.as_view(), name='detail'),
    path('<int:pk>/start/', CampaignStartView.as_view(), name='start'),
    path('<int:campaign_id>/invitees/', CampaignInviteeListView.as_view(), name='invitees'),
]
