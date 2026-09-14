from django.urls import path
from .views import InviteeImportView, InviteeListView

app_name = 'invitees'

urlpatterns = [
    path('import/', InviteeImportView.as_view(), name='import'),
    path('', InviteeListView.as_view(), name='list'),
]
