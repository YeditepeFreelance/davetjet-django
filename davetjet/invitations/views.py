from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from .models import Invitation
from .forms import InvitationForm
from projects.models import Project
from django.contrib.auth.mixins import LoginRequiredMixin

class EditInvitationView(LoginRequiredMixin, TemplateView):
    model = Invitation
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'
    template_name = 'dashboard/invitations/edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invitation'] = Invitation.objects.filter(project__owner=self.request.user, id=self.kwargs.get('pk')).first()
        return context

class InvitationsListView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/invitations/index.html'
    login_url = 'core:login'
    redirect_field_name = 'next'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.filter(owner=self.request.user)
        return context
