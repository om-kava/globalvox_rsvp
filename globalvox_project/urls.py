from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # API Endpoints will be mounted here
    path('api/auth/', include('apps.accounts.urls')),
    path('api/campaigns/', include('apps.campaigns.urls')),
    path('api/invitees/', include('apps.invitees.urls')),
]
