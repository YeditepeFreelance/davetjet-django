# recipients/views.py
import json
import sys
import csv
from io import StringIO, TextIOWrapper

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (
    JsonResponse,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.response import Response

from recipients.forms import RecipientForm
from .models import Recipient
from invitations.models import Invitation
from projects.models import Project  # <- projects.models'tan
from .utils import process_recipient_file, get_recipient_usage
from .serializers import RecipientNameSerializer, RSVPUpdateSerializer


# ----- Kota Endpoints -----
@method_decorator(login_required, name="dispatch")
class RecipientQuotaView(View):
    def get(self, request):
        # (Opsiyonel) Proje erişim doğrulaması
        project_id = request.GET.get("project_id")
        if project_id:
            get_object_or_404(Project, id=project_id, owner=request.user)
        data = get_recipient_usage(request.user)
        return JsonResponse(data)


# ----- Autocomplete -----
@api_view(['GET'])
def recipient_autocomplete(request):
    query = request.GET.get('q', '')
    recipients = Recipient.objects.filter(name__icontains=query)[:5]
    serializer = RecipientNameSerializer(recipients, many=True)
    return Response(serializer.data)


# ----- RSVP Update -----
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


# ----- Davetiye bazlı autocomplete & update -----
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # 🔓 Login gereksinimini kaldır
@authentication_classes([SessionAuthentication, BasicAuthentication])  # CSRF koruması kalsın
def recipients_handler(request, invitation_slug=None):
    """
    GET  → /recipients/<slug>/?q=...
    POST → /recipients/<slug>/  { name, status }   (status: yes|no|maybe)
    Not: Login gerekmez; CSRF korunur (fetchte X-CSRFToken ve credentials:'same-origin' gönderin).
    """
    invitation = get_object_or_404(Invitation, slug=invitation_slug)
    if invitation.project.recipients.count() > invitation.recipients.count():
        invitation.recipients.set(invitation.project.recipients.all())
        invitation.save()

    # (Opsiyonel) Şifreli davet ise token doğrula — sayfa erişiminde zaten kontrol yapıyorsan gerekmez.
    # access_token = request.GET.get("access") or request.headers.get("X-Access-Token")
    # if invitation.is_password_protected and access_token:
    #     if not match_invitation(invitation, access_token):
    #         return Response({"error": "Erişim tokeni geçersiz."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        q = (request.GET.get("q") or "").strip()
        if not q:
            return Response([], status=status.HTTP_200_OK)
        recipients = invitation.recipients.filter(name__icontains=q).only("id", "name")[:5]
        return Response(RecipientNameSerializer(recipients, many=True).data)

    # POST
    name = (request.data.get("name") or "").strip()
    status_value = (request.data.get("status") or "").strip().lower()

    if not name:
        return Response({"error": "İsim gerekli."}, status=status.HTTP_400_BAD_REQUEST)
    if status_value not in {"yes", "no", "maybe"}:
        return Response({"error": "Geçersiz katılım durumu."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        recipient = invitation.recipients.get(name=name)
    except Recipient.DoesNotExist:
        return Response({"error": "Bu davetiyeye ait böyle bir kişi yok."}, status=status.HTTP_404_NOT_FOUND)

    recipient.rsvp_status = status_value
    recipient.save(update_fields=["rsvp_status"])
    return Response({"message": f"{recipient.name} için katılım durumu güncellendi"}, status=status.HTTP_200_OK)
# ----- Edit Recipient (tek kayıt) -----
class EditRecipientView(LoginRequiredMixin, View):
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'

    def post(self, request, *args, **kwargs):
        recipient_id = request.POST.get('recipient_id')
        # M2M: projects__owner
        recipient = Recipient.objects.filter(id=recipient_id, project__owner=request.user).first()
        if not recipient:
            return HttpResponse("Recipient not found or you do not have permission to edit it.", status=404)

        recipient.name = request.POST.get('name', recipient.name)
        recipient.email = request.POST.get('email', recipient.email)
        recipient.phone_number = request.POST.get('phone_number', recipient.phone_number)
        recipient.save()
        return HttpResponse("Recipient updated successfully.", status=200)


# ----- Delete Recipient -----
class DeleteRecipientView(LoginRequiredMixin, View):
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        recipient_id = kwargs.get('pk')
        if not recipient_id:
            return HttpResponse("Recipient ID is required.", status=400)
        # M2M: projects__owner
        recipient = Recipient.objects.filter(id=recipient_id, project__owner=request.user).first()
        if not recipient:
            return HttpResponse("Recipient not found or you do not have permission to delete it.", status=404)
        recipient.delete()
        return HttpResponse("Recipient deleted successfully.", status=200)


# ----- Import CSV (kota kontrollü) -----
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

            # ---- KOTA: kalan hak
            quota = get_recipient_usage(request.user)
            remaining = int(quota.get("remaining", 0))
            if remaining <= 0:
                return HttpResponseForbidden("RECIPIENT_QUOTA_EXCEEDED")

            # ---- Dosyayı önce hızlıca say (yaklaşık plan)
            try:
                wrapper = TextIOWrapper(file.file, encoding="utf-8", newline="")
                reader = csv.DictReader(wrapper)
                planned = 0
                for row in reader:
                    name = (row.get("name") or row.get("Name") or "").strip()
                    email = (row.get("email") or row.get("Email") or "").strip()
                    phone = (row.get("phone_number") or row.get("phone") or "").strip()
                    if name or email or phone:
                        planned += 1
            finally:
                # process_recipient_file tekrar okuyabilsin
                try:
                    file.seek(0)
                except Exception:
                    pass

            if planned > remaining:
                return HttpResponse(
                    f"You can add at most {remaining} more recipients (planned={planned}).",
                    status=400,
                )

            # ---- Asıl işleme
            res = process_recipient_file(file, project=project)
            # process_recipient_file farklı bir format dönebilir; string gösterim yeterli
            added = len(res) if hasattr(res, "__len__") else 0
            return HttpResponse(f"Successfully imported {added} recipients.", status=200)

        except ValueError as e:
            return HttpResponse(str(e), status=400)


# ----- Export CSV -----
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

        df = pd.DataFrame(list(recipients.values('name', 'email', 'phone_number')))
        buffer = StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="recipients_{project_id}.csv"'
        return response


# ----- Edit List (UI) -----
class EditRecipientListView(LoginRequiredMixin, TemplateView):
    model = Recipient
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'
    template_name = 'dashboard/recipients/edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = Project.objects.filter(owner=self.request.user).first()
        context['recipient_quota_json'] = json.dumps(get_recipient_usage(self.request.user))
        return context


class ViewRecipientListView(LoginRequiredMixin, TemplateView):
    model = Recipient
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'
    template_name = 'dashboard/recipients/index.html'

    def get(self, request, *args, **kwargs):
        inv = Invitation.objects.filter(project__owner=request.user).first()
        if not inv:
            return redirect('core:create-invitation')

        return redirect('core:edit-recipients', inv.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.filter(owner=self.request.user)
        return context


# ----- Create (manuel ekleme – kota + M2M) -----
class CreateRecipientView(FormView):
    template_name = "dashboard/recipients/edit.html"
    form_class = RecipientForm
    success_url = reverse_lazy('core:recipients')

    def form_valid(self, form):
        # Proje zorunlu: modal formdan geliyor
        project_id = self.request.POST.get("project_id")
        project = Project.objects.filter(owner=self.request.user, id=project_id).first()
        if not project:
            # AJAX beklentisi varsa düz metin döner
            if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return HttpResponseBadRequest("Project not found or permission denied.")
            messages.error(self.request, "Proje bulunamadı veya erişim izniniz yok.")
            return redirect(self.success_url)

        # KOTA kontrol
        quota = get_recipient_usage(self.request.user)
        remaining = int(quota.get("remaining", 0))
        if remaining <= 0:
            if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return HttpResponseForbidden("RECIPIENT_QUOTA_EXCEEDED")
            messages.error(self.request, "Davetli hakkınız tükendi.")
            return redirect(self.success_url)

        # Kayıt + M2M bağla
        obj = form.save(commit=False)
        obj.save()
        # M2M: projects
        obj.project.add(project)
        obj.save()

        messages.success(self.request, "Alıcı oluşturuldu.")

        # Modal (AJAX) ise sadece 'OK' döndür
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return HttpResponse("OK", status=200)

        return redirect(self.success_url)

    def form_invalid(self, form):
        import logging
        logging.getLogger(__name__).error("Recipient form errors: %s", form.errors.get_json_data())
        # AJAX ise 400 ve hata metni
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return HttpResponseBadRequest("; ".join([f"{k}:{','.join(v)}" for k, v in form.errors.items()]))
        messages.error(self.request, "Form hataları var, lütfen kontrol edin.")
        return self.render_to_response(self.get_context_data(form=form))
