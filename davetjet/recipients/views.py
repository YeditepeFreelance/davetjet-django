import sys
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
import pandas as pd
from io import BytesIO, StringIO

from recipients.forms import RecipientForm
from .models import Recipient
from invitations.models import Invitation
from projects.models import Project
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import process_recipient_file
from .serializers import RecipientNameSerializer, RSVPUpdateSerializer

@api_view(['GET'])
def recipient_autocomplete(request):
    query = request.GET.get('q', '')
    recipients = Recipient.objects.filter(name__icontains=query)[:5]
    serializer = RecipientNameSerializer(recipients, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def rsvp_update(request):
    name = request.data.get('name')
    status_value = request.data.get('status')

    try:
        recipient = Recipient.objects.get(name=name)
    except Recipient.DoesNotExist:
        return Response({"error": "Kişi bulunamadı"}, status=status.HTTP_404_NOT_FOUND)

    recipient.rsvp_status = status_value
    recipient.save(update_fields=['rsvp_status'])
    return Response({"message": "Katılım durumu güncellendi"})


@api_view(['GET', 'POST'])
def recipients_handler(request, invitation_slug=None):
    """
    GET  → /recipients/?q=...
    POST → /recipients/ { name, status }
    invitation_slug → davetiyeye ait kontrol
    """
    try:
        invitation = Invitation.objects.get(slug=invitation_slug)
    except Invitation.DoesNotExist:
        return Response({"error": "Davet bulunamadı"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        # Autocomplete → sadece bu davetiyedeki kişiler
        query = request.GET.get("q", "")
        recipients = invitation.recipients.filter(name__icontains=query)[:5]
        serializer = RecipientNameSerializer(recipients, many=True)
        return Response(serializer.data)

    elif request.method == "POST":
        name = request.data.get("name")
        status_value = request.data.get("status")

        try:
            recipient = invitation.recipients.get(name=name)
        except Recipient.DoesNotExist:
            return Response({"error": "Bu davetiyeye ait böyle bir kişi yok."}, status=status.HTTP_404_NOT_FOUND)

        if status_value not in ["yes", "no", "maybe"]:
            return Response({"error": "Geçersiz katılım durumu"}, status=status.HTTP_400_BAD_REQUEST)

        recipient.rsvp_status = status_value
        recipient.save(update_fields=['rsvp_status'])

        return Response({"message": f"{recipient.name} için katılım durumu güncellendi"})

class EditRecipientView(LoginRequiredMixin, View):
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'

    def post(self, request, *args, **kwargs):
        recipient_id = request.POST.get('recipient_id')
        recipient = Recipient.objects.filter(id=recipient_id, project__owner=request.user).first()
        if not recipient:
            return HttpResponse("Recipient not found or you do not have permission to edit it.", status=404)

        recipient.name = request.POST.get('name', recipient.name)
        recipient.email = request.POST.get('email', recipient.email)
        recipient.save()
        return HttpResponse("Recipient updated successfully.", status=200)

class DeleteRecipientView(LoginRequiredMixin, View):
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        recipient_id = kwargs.get('pk')
        if not recipient_id:
            return HttpResponse("Recipient ID is required.", status=400)
        recipient = Recipient.objects.filter(id=recipient_id, project__owner=request.user).first()
        if not recipient:
            return HttpResponse("Recipient not found or you do not have permission to delete it.", status=404)
        recipient.delete()
        return HttpResponse("Recipient deleted successfully.", status=200)

class ImportRecipientsView(LoginRequiredMixin, View):
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'

    def post(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return HttpResponse("No file uploaded.", status=400)
        
        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return HttpResponse("Invalid file format. Please upload a CSV file.", status=400)

        try:
            project = Project.objects.filter(owner=request.user, id=request.POST.get('project_id')).first()
               
            if not project:
                return HttpResponse("Project not found or you do not have permission to access it.", status=404)
            res = process_recipient_file(file, project=project)
            return HttpResponse(f"Successfully imported {len(res)} recipients.", status=200)
        except ValueError as e:
            print(str(e))
            return HttpResponse(str(e), status=400)

class ExportRecipientsView(LoginRequiredMixin, View):
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        project_id = request.GET.get('project_id')
        if not project_id:
            return HttpResponse("Project ID is required.", status=400)
        
        project = Project.objects.filter(owner=request.user, id=project_id).first()
        if not project:
            return HttpResponse("Project not found or you do not have permission to access it.", status=404)

        recipients = project.recipients.all()
        if not recipients:
            return HttpResponse("No recipients found for this project.", status=404)

        df = pd.DataFrame(list(recipients.values('name', 'email')))
        buffer = StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="recipients_{project_id}.csv"'
        return response


class EditRecipientListView(LoginRequiredMixin, TemplateView):
    model = Recipient
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'
    template_name = 'dashboard/recipients/edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = Project.objects.filter(owner=self.request.user, id=self.kwargs.get('pk')).first()
        return context

class ViewRecipientListView(LoginRequiredMixin, TemplateView):
    model = Recipient
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'
    template_name = 'dashboard/recipients/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.filter(owner=self.request.user)
        return context
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.contrib import messages

class CreateRecipientView(FormView):
    template_name = "dashboard/recipients/edit.html"  # elindeki bir template'i koy
    form_class = RecipientForm
    success_url = reverse_lazy('core:recipients')

    def form_valid(self, form):
        obj = form.save()
        messages.success(self.request, "Alıcı oluşturuldu.")
        project = Project.objects.filter(owner=self.request.user).first()
        obj.project.add(project)
        obj.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        # konsola da yaz, sayfada da göster
        import logging
        logging.getLogger(__name__).error("Recipient form errors: %s", form.errors.get_json_data())
        messages.error(self.request, "Form hataları var, lütfen kontrol edin.")
        return self.render_to_response(self.get_context_data(form=form))
