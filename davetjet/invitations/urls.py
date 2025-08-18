from django.urls import path

from .views import ShowInvitationView
from . import api

app_name = 'invitations'

urlpatterns = [
  path('<slug:slug>/', ShowInvitationView.as_view(), name='show'),  
      path("api/drafts/", api.list_drafts, name="invitation-drafts"),
      path("api/schedule-send/<int:pk>/", api.schedule_send, name="invitation-schedule-send"),
    path("api/drafts/<int:pk>/promote/", api.promote_draft, name="invitation-draft-promote"),
    path("api/drafts/<int:pk>/", api.delete_draft, name="invitation-draft-delete"),
        path("api/edit/<int:pk>/", api.invitation_detail, name="invitation-detail"),
 path("api/analytics/invitations/", api.analytics_list_invitations, name="analytics-inv-list"),
    path("api/analytics/overview/", api.analytics_overview, name="analytics-overview"),
    path("api/analytics/invitations/<int:pk>/", api.analytics_invitation_detail, name="analytics-inv-detail"),
    path(
        "api/analytics/invitations/<slug:key>/recipients/",
        api.analytics_invitation_recipients,
        name="analytics-inv-recipients",
    ),
]