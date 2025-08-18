import os
import base64
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect
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
from .utils import match_invitation  # Fernet doğrulaması


from invitations.utils import match_invitation
from .serializers import InvitationSerializer, CreateInvitationSerializer
from .models import Invitation
from .forms import InvitationForm
from projects.models import Project



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

class CreateInvitationView(LoginRequiredMixin, CreateView):
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

# Access token generation

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
        # sadece id seçicilerini destekliyoruz burada
        if selector.startswith("#"):
            el["id"] = selector[1:]
        parent.append(el)
    return el
@method_decorator(ensure_csrf_cookie, name='dispatch')
class ShowInvitationView(TemplateView):
    # template_name kullanmıyoruz; doğrudan parse edip HTML döndürüyoruz
    def get(self, request, slug):
        try:
            invitation = Invitation.objects.select_related("project").prefetch_related("recipients").get(slug=slug)
        except Invitation.DoesNotExist:
            raise Http404("Davet bulunamadı.")

        if invitation.is_expired():
            return HttpResponse("Bu davet süresi dolmuştur.", status=410)

        # 🔐 Şifre/erişim kontrolü (Fernet token öncelikli)
        if invitation.is_password_protected:
            access_token = request.GET.get("access")
            if access_token:
                if not match_invitation(invitation, access_token):
                    return HttpResponse("Erişim tokeni geçersiz.", status=403)
            else:
                password = request.GET.get("password")
                if not password:
                    return HttpResponse("Şifre gerekli.", status=403)
                if password != invitation.password:
                    return HttpResponse("Şifre hatalı.", status=403)

        # 📄 Statik şablonu oku
        template_path = os.path.join(settings.BASE_DIR, "static", "inv-temps", f"{invitation.template}.html")
        if not os.path.exists(template_path):
            return HttpResponse("Şablon bulunamadı", status=404)

        with open(template_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # 🧪 Tarih/saat parçaları
        dt = invitation.invitation_date
        date_str = dt.strftime("%d.%m.%Y") if dt else ""
        time_str = dt.strftime("%H:%M") if dt else ""

        # 📝 Metin yerleştirmeleri – element yoksa oluştur
        mapping = {
            "#event-title": invitation.name,
            "#event-date": date_str,
            "#event-time": time_str,
            "#event-message": invitation.message or "",
            "#event-location": getattr(invitation, "location", "") or "",
        }
        for css_sel, val in mapping.items():
            el = soup.select_one(css_sel) or _ensure_el(soup, css_sel, "span")
            _set_text(el, val)

        # 🔗 Slug / link / gizli input gibi yardımcı hedefler
        slug_el = soup.select_one("#inv-slug")
        if slug_el:
            _set_text(slug_el, invitation.slug)

        rsvp_link = soup.select_one("#rsvp-link")
        if rsvp_link:
            _set_attr(rsvp_link, "href", f"/i/{invitation.slug}")

        slug_input = soup.select_one("#inv-slug-input")
        if slug_input:
            _set_attr(slug_input, "value", invitation.slug)

        # ✍️ E-posta/sunum için contenteditable alanları kapat
        for tag in soup.find_all(attrs={"contenteditable": True}):
            del tag["contenteditable"]

        # (Opsiyonel) 🎯 İsim önerileri için davetlileri tek seferde göm
        # Şablonun <body> sonunda JSON script bloğu ekliyoruz.
        recipients = invitation.recipients.all().only("id", "name")
        data_tag = soup.new_tag("script", type="application/json", id="inv-recipients")
        data_tag.string = json.dumps([{"id": r.id, "name": r.name} for r in recipients], ensure_ascii=False)
        # Eğer body yoksa soup'e ekle
        (soup.body or soup).append(data_tag)

        # (Opsiyonel) Küçük inline yardımcı JS – hiçbir dış import yoksa:
        # Bu bloğu istersen çıkar; senin mevcut JS’in de bu JSON’u okuyabilir.
        helper_js = soup.new_tag("script")
        helper_js.string = """
        (function(){
          // Örnek: sayfada RECIPIENTS sabiti hazır olsun
          try {
            const raw = document.getElementById('inv-recipients')?.textContent || '[]';
            window.RECIPIENTS = JSON.parse(raw);
          } catch(e){ window.RECIPIENTS = []; }
        })();
        """
        (soup.body or soup).append(helper_js)

        return HttpResponse(str(soup), content_type="text/html; charset=utf-8")
