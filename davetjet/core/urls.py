from django.shortcuts import render
from django.urls import path
from users.views import CustomLoginView, CustomRegisterView, LogOutView, DashboardSettingsView, DashboardProfileView, ForgetPasswordView
from recipients.views import ViewRecipientListView, EditRecipientListView
from invitations.views import InvitationsListView, EditInvitationView, CreateInvitationView, CreateInvitationAPI
from .views import DashboardView, SearchAPIView, InvitationEditView, SendingView, HomePageView, AnalyticsView, SubscribeView, SubscribeNextView, SubscribeSuccessView, SubscribeFailView, PackageView
from payments.views import paytr_notify

app_name = 'core'

urlpatterns = [
    path('', HomePageView.as_view(), name='index'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/settings/', DashboardSettingsView.as_view(), name='settings'),
    path('dashboard/profile/', DashboardProfileView.as_view(), name='profile'),
    path('dashboard/recipients/', ViewRecipientListView.as_view(), name='recipients'),
    path('dashboard/recipients/<int:pk>/', EditRecipientListView.as_view(), name='edit-recipients'),
    path('dashboard/invitations/', InvitationsListView.as_view(), name='invitations'),
    path('dashboard/invitations/<int:pk>/', EditInvitationView.as_view(), name='edit-invitation'),
    path('dashboard/invitations/create-new', CreateInvitationView.as_view(), name='create-invitation'),
    path('dashboard/invitations/edit/<int:pk>/', InvitationEditView.as_view(), name='edit-invitation-api'),
    path('dashboard/subscribe/', SubscribeView.as_view(), name='subscribe'),
    path('dashboard/subscribe/next/<int:pk>/', SubscribeNextView.as_view(), name='subscribe-next'),
    path('dashboard/subscribe/success', SubscribeSuccessView.as_view(), name='subscribe-success'),
    path('dashboard/subscribe/fail', SubscribeFailView.as_view(), name='subscribe-fail'),
    path('dashboard/package/', PackageView.as_view(), name='package'),
    path('dashboard/analytics/', AnalyticsView.as_view(), name='analytics'),
    path('dashboard/sending/', SendingView.as_view(), name='sending'),
    # path('subscribe/', lambda request: render(request, 'utils/modal-subscribe.html'), name='modal-subscribe'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('forget-password/', ForgetPasswordView.as_view(), name='forget-password'),
    path('register/', CustomRegisterView.as_view(), name='register'),
    path('logout/', LogOutView.as_view(), name='logout'),

    path('api/search/', SearchAPIView.as_view(), name='search-api'),
    path('api/invitations/create/', CreateInvitationAPI.as_view(), name='create-invitation-api'),
    path('paytr/notify/', paytr_notify, name='paytr-notify'),

]

