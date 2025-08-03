from django.shortcuts import render
from django.urls import path
from users.views import CustomLoginView, CustomRegisterView, LogOutView, DashboardSettingsView, DashboardProfileView
from recipients.views import ViewRecipientListView, EditRecipientListView
from invitations.views import InvitationsListView, EditInvitationView
from .views import DashboardView, SearchAPIView

app_name = 'core'

urlpatterns = [
    path('', lambda request: render(request, 'landing/index.html'), name='index'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/settings/', DashboardSettingsView.as_view(), name='settings'),
    path('dashboard/profile/', DashboardProfileView.as_view(), name='profile'),
    path('dashboard/recipients/', ViewRecipientListView.as_view(), name='recipients'),
    path('dashboard/recipients/<int:pk>/', EditRecipientListView.as_view(), name='edit-recipients'),
    path('dashboard/invitations/', InvitationsListView.as_view(), name='invitations'),
    path('dashboard/invitations/<int:pk>/', EditInvitationView.as_view(), name='edit-invitation'),
    path('dashboard/subscribe/', lambda request: render(request, 'dashboard/subscribe.html'), name='subscribe'),
    path('dashboard/package/', lambda request: render(request, 'dashboard/package.html'), name='package'),
    # path('subscribe/', lambda request: render(request, 'utils/modal-subscribe.html'), name='modal-subscribe'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('register/', CustomRegisterView.as_view(), name='register'),
    path('logout/', LogOutView.as_view(), name='logout'),

    path('api/search/', SearchAPIView.as_view(), name='search-api'),
]