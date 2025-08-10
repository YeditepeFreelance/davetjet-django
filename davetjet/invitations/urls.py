from django.urls import path

from .views import ShowInvitationView
from . import api

app_name = 'invitations'

urlpatterns = [
  path('<slug:slug>/', ShowInvitationView.as_view(), name='show'),  
      path("api/drafts/", api.list_drafts, name="invitation-drafts"),
    path("api/drafts/<int:pk>/promote/", api.promote_draft, name="invitation-draft-promote"),
    path("api/drafts/<int:pk>/", api.delete_draft, name="invitation-draft-delete"),
        path("api/edit/<int:pk>/", api.invitation_detail, name="invitation-detail"),

]