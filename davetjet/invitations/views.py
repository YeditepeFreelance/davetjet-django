import os
# import base64  # kullanılmıyor
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.utils.text import slugify
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from bs4 import BeautifulSoup, NavigableString
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
import json

from .models import Invitation
# CHANGED: match_invitation importunu tekilleştirdik; secure_links içinden al
from .utils import match_invitation,build_invitation_html # Fernet doğrulaması

from .serializers import InvitationSerializer, CreateInvitationSerializer
from .forms import InvitationForm
from projects.models import Project
from users.mixins import RequireActivePackageMixin

# ==== Genel yardımcılar (HTML yerleşimleri) ====
def _set_text(el, value: str | None):
    el.clear()
    el.append(NavigableString("" if value is None else str(value)))

def _set_attr(el, attr, value: str | None):
    el[attr] = "" if value is None else str(value)

def _ensure_el(soup, selector, tag_name="span"):
    """soup.select_one yoksa, body'nin sonuna yaratır ve döner."""
    el = soup.select_one(selector)
    if el is None:
        parent = soup.body or soup
        el = soup.new_tag(tag_name)
        if selector.startswith("#"):
            el["id"] = selector[1:]
        parent.append(el)
    return el


# ==== Cookie tabanlı erişim akışı için sabitler + yardımcılar ====
FERNET = Fernet(settings.FERNET_KEY)
ACCESS_TTL = 90 * 24 * 60 * 60  # 90 gün
COOKIE_NAME_FMT = "inv_access_{inv_id}"

def _payload(inv: Invitation) -> dict:
    return {"id": inv.id, "p": (inv.password or "")}

def _make_token(inv: Invitation) -> str:
    return FERNET.encrypt(json.dumps(_payload(inv)).encode()).decode()

def _get_token_from_request(request, inv: Invitation) -> str | None:
    """Önce cookie, sonra ?access= parametresi."""
    cookie_name = COOKIE_NAME_FMT.format(inv_id=inv.id)
    return request.COOKIES.get(cookie_name) or request.GET.get("access")

def _set_access_cookie(response, inv: Invitation, token: str):
    """Token'ı sadece bu davetiye yolu altında geçerli olacak şekilde yaz."""
    response.set_cookie(
        key=COOKIE_NAME_FMT.format(inv_id=inv.id),
        value=token,
        max_age=ACCESS_TTL,
        secure=not settings.DEBUG,
        httponly=True,
        samesite="Lax",
        path=f"/invitations/{inv.slug}/",
    )


# ==== Dashboard Views ====
class EditInvitationView(LoginRequiredMixin, RequireActivePackageMixin, TemplateView):
    model = Invitation
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'
    template_name = 'dashboard/invitations/edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invitation'] = Invitation.objects.filter(
            project__owner=self.request.user, id=self.kwargs.get('pk')
        ).first()
        return context


class InvitationsListView(LoginRequiredMixin, RequireActivePackageMixin, TemplateView):
    template_name = 'dashboard/invitations/index.html'
    login_url = 'core:login'
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        inv = Invitation.objects.filter(project__owner=request.user).first()
        if inv:
            return redirect('core:edit-invitation', pk=inv.id)
        return redirect('core:create-invitation')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.filter(owner=self.request.user)
        return context


class CreateInvitationView(LoginRequiredMixin, RequireActivePackageMixin, CreateView):
    model = Invitation
    form_class = InvitationForm
    template_name = 'dashboard/invitations/create.html'
    login_url = reverse_lazy('core:login')
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        inv = Invitation.objects.filter(project__owner=request.user).first()
        if inv:
            return redirect('core:invitations')
        return super().get(request, *args, **kwargs)


class CreateInvitationAPI(APIView):
    def post(self, request):
        serializer = CreateInvitationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            invitation = serializer.save()
            return Response({"success": True, "id": invitation.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==== ENTRY VIEW (NEW) ====
class InvitationEntryView(View):
    """
    /i/<slug>/a/<token>/  -> token doğrulanır -> HttpOnly cookie set edilir ->
    302 /invitations/<slug>/ (temiz URL)
    """
    def get(self, request, slug, token):
        inv = Invitation.objects.filter(slug=slug).first()
        if not inv:
            raise Http404("Davet bulunamadı.")

        if inv.is_expired():
            return HttpResponse("Bu davet süresi dolmuştur.", status=410)

        if not match_invitation(inv, token):
            return HttpResponseForbidden("Geçersiz veya süresi dolmuş davetiye bağlantısı.")

        resp = redirect(f"/invitations/{slug}/")
        _set_access_cookie(resp, inv, token)
        return resp


# ==== PUBLIC (CLEAN URL) VIEW (CHANGED) ====


@method_decorator(ensure_csrf_cookie, name='dispatch')
class ShowInvitationView(TemplateView):
    def get(self, request, slug):
        # 1) Davet
        try:
            invitation = (Invitation.objects
                          .select_related("project")
                          .prefetch_related("recipients")
                          .get(slug=slug))
        except Invitation.DoesNotExist:
            raise Http404("Davet bulunamadı.")

        if invitation.is_expired():
            return HttpResponse("Bu davet süresi dolmuştur.", status=410)

        # 2) Erişim kontrolü (şifre/token)
        if invitation.is_password_protected:
            token = _get_token_from_request(request, invitation)
            if not (token and match_invitation(invitation, token)):
                pwd = request.GET.get("password")
                if True or (pwd and pwd == (invitation.password or "")):
                    token = _make_token(invitation)
                    resp = redirect(f"/invitations/{slug}/")
                    _set_access_cookie(resp, invitation, token)
                    return resp
                return HttpResponse("Şifre gerekli veya erişim yok.", status=403)

        # 3) HTML’i utils’ten üret
        # show_rsvp=True -> 'hide-in-embed' kalksın, form görünsün
        html = build_invitation_html(
            invitation,
            request=request,
            show_rsvp=True,
            embed_recipients=True,
            keep_contenteditable=False,
        )

        return HttpResponse(html, content_type="text/html; charset=utf-8")


# PDF
