import os
# import base64  # kullanılmıyor
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseForbidden
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
# CHANGED: match_invitation importunu tekilleştirdik; secure_links içinden al
from .utils import match_invitation  # Fernet doğrulaması

from .serializers import InvitationSerializer, CreateInvitationSerializer
from .forms import InvitationForm
from projects.models import Project


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
class EditInvitationView(LoginRequiredMixin, TemplateView):
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


class InvitationsListView(LoginRequiredMixin, TemplateView):
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
    # template_name kullanmıyoruz; doğrudan parse edip HTML döndürüyoruz
    def get(self, request, slug):
        try:
            invitation = Invitation.objects.select_related("project").prefetch_related("recipients").get(slug=slug)
        except Invitation.DoesNotExist:
            raise Http404("Davet bulunamadı.")

        if invitation.is_expired():
            return HttpResponse("Bu davet süresi dolmuştur.", status=410)

        # 🔐 Şifre/erişim kontrolü
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

        # 📄 ŞABLON KAYNAĞI: Önce inline HTML (template_html), yoksa statik dosya
        markup = (invitation.template_html or "").strip()
        if markup:
            soup = BeautifulSoup(markup, "html.parser")
        else:
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
            _set_attr(rsvp_link, "href", f"/invitations/{invitation.slug}/")

        slug_input = soup.select_one("#inv-slug-input")
        if slug_input:
            _set_attr(slug_input, "value", invitation.slug)

        # ✍️ Yayın sayfasında contenteditable'ları kapat (kamu görünümü)
        for tag in soup.find_all(attrs={"contenteditable": True}):
            try:
                del tag["contenteditable"]
            except Exception:
                pass

        # (Opsiyonel) 🎯 İsim önerileri için davetlileri göm
        recipients = invitation.recipients.all().only("id", "name")
        data_tag = soup.new_tag("script", type="application/json", id="inv-recipients")
        data_tag.string = json.dumps([{"id": r.id, "name": r.name} for r in recipients], ensure_ascii=False)
        (soup.body or soup).append(data_tag)

        # (Opsiyonel) Küçük inline yardımcı JS
        helper_js = soup.new_tag("script")
        helper_js.string = """
        (function(){
          try {
            const raw = document.getElementById('inv-recipients')?.textContent || '[]';
            window.RECIPIENTS = JSON.parse(raw);
          } catch(e){ window.RECIPIENTS = []; }
        })();
        """
        (soup.body or soup).append(helper_js)
        # --- RSVP görünürlüğü: .rsvp içinden 'hide-in-embed' sınıfını kaldır

        for rsvp in soup.select("section.rsvp"):
            classes = rsvp.get("class", [])
            if "hide-in-embed" in classes:
                rsvp["class"] = [c for c in classes if c != "hide-in-embed"]

        # --- RSVP hiç yoksa, minimal bir formu fallback olarak ekle (opsiyonel)
        if not soup.select_one("section.rsvp"):
            rsvp = soup.new_tag("section", **{
                "class": "rsvp", "aria-labelledby": "rsvpTitle", "id": "rsvpRoot"
            })
            rsvp.inner_html = None  # sadece referans, BeautifulSoup'ta kullanılmıyor

            # içerik
            rsvp_header = soup.new_tag("h2", id="rsvpTitle")
            rsvp_header.string = "Katılım Bildirimi"
            rsvp.append(rsvp_header)

            row = soup.new_tag("div", **{"class": "row", "style": "margin-bottom:10px"})
            inp = soup.new_tag("input", id="rsvp-name", **{
                "class": "input", "type": "text", "placeholder": "Adınız", "autocomplete": "off"
            })
            row.append(inp)
            rsvp.append(row)

            chips = soup.new_tag("div", **{"class": "chips", "role": "group", "aria-label": "Katılım durumu"})
            for label, val in [("Geleceğim","yes"), ("Emin Değilim","maybe"), ("Gelmeyeceğim","no")]:
                chip = soup.new_tag("div", **{"class": "chip", "tabindex":"0"})
                chip["data-status"] = val
                chip.string = label
                chips.append(chip)
            rsvp.append(chips)

            btn = soup.new_tag("button", id="rsvp-submit", **{"class":"btn", "disabled": True})
            btn.string = "Gönder"
            rsvp.append(btn)

            msg = soup.new_tag("div", id="rsvp-msg", **{"class":"msg"})
            rsvp.append(msg)

            # nereye ekleyelim? divider'ın altına, yoksa body’nin sonuna
            anchor = soup.select_one(".divider-soft")
            if anchor and hasattr(anchor, "insert_after"):
                anchor.insert_after(rsvp)
            else:
                (soup.body or soup).append(rsvp)

        return HttpResponse(str(soup), content_type="text/html; charset=utf-8")