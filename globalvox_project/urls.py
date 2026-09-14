from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Web Dashboard UI
    path('', TemplateView.as_view(template_name='index.html'), name='dashboard_home'),
    # REST API Endpoints
    path('api/auth/', include('apps.accounts.urls')),
    path('api/campaigns/', include('apps.campaigns.urls')),
    path('api/invitees/', include('apps.invitees.urls')),
]
