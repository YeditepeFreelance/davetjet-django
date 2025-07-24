from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from .models import Invitation
from .forms import InvitationForm
from projects.models import Project

class InvitationTestView(TemplateView):
    """
    A simple test view to check if the invitations app is working.
    """
    template_name = 'invitations/test.html'

    def get(self, request, *args, **kwargs):
        # Custom logic can be added here if needed
        return render(request, self.template_name, context={
            'projects': Project.objects.filter(owner=request.user),
            'invitations': Invitation.objects.filter(project__owner=request.user)
        })

class InvitationCreateView(CreateView):
    """
    A view to create a new invitation.
    """
    model = Invitation
    template_name = 'invitations/test.html'
    fields = ['name', 'message', 'project']
    success_url = reverse_lazy('invitations:test')

    def form_valid(self, form):
        # Custom logic can be added here before saving the form
        return super().form_valid(form)

class InvitationEditView(View):
    """
    A view to edit an existing invitation.
    """
    
    def get(self, request, pk):
        invitation = Invitation.objects.get(pk=pk)
        return render(request, 'invitations/edit.html', {'invitation': invitation, 'form': InvitationForm(instance=invitation)})

    def post(self, request, pk):
        invitation = Invitation.objects.get(pk=pk)
        form = InvitationForm(request.POST, instance=invitation)
        if form.is_valid():
            form.save()
            return redirect('invitations:test')
        return render(request, 'invitations/edit.html', {'form': form, 'invitation': invitation})

class InvitationDeleteView(View):
    """
    A view to delete an existing invitation.
    """
    
    def get(self, request, pk):
        invitation = Invitation.objects.get(pk=pk)
        invitation.delete()
        return redirect('invitations:test')

# To be added later:

# class InvitationDetailView(View):
# class InvitationManageView(View):
# class InvitationSendView(View):

# Analytics dashboard functionalitiy and utility functions can be added here as needed.