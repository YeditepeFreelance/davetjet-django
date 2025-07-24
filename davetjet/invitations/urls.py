from django.urls import path
from .views import InvitationTestView, InvitationCreateView, InvitationEditView, InvitationDeleteView

app_name = 'invitations'

urlpatterns = [
  path('test/', InvitationTestView.as_view(), name='test'),
  path('create/', InvitationCreateView.as_view(), name='create'),
  path('edit/<int:pk>', InvitationEditView.as_view(), name='edit'),
  path('delete/<int:pk>', InvitationDeleteView.as_view(), name='delete'),
]