import base64
from datetime import datetime
import json
import sys
import uuid

from django.shortcuts import render
from django.views import View
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin

import requests
from rest_framework.views import APIView
from django.views.generic import TemplateView
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from payments.models import Payment, Plan
from invitations.models import Invitation
from invitations.serializers import InvitationSerializer
from projects.models import Project
from users.decorators import require_full_access
from users.mixins import RequireActivePackageMixin
from django.utils.decorators import method_decorator
import davetjet.settings as settings

import base64
import hmac
import hashlib
import json
import random
import string


STATIC_COMMANDS = [
    {"id": "cmd_logout", "label": "Command: Logout", "type": "command", "url": "/logout/"},
    {"id": "cmd_mute_notifications", "label": "Command: Mute Notifications", "type": "command", "url": "#"},
    {"id": "cmd_help", "label": "Command: Help", "type": "command", "url": "/dashboard/"},
]

STATIC_PAGES = [
    {"id": "page_dashboard", "label": "Page: Dashboard", "type": "page", "url": "/dashboard/"},
    {"id": "page_profile", "label": "Page: Profile", "type": "page", "url": "/dashboard/settings/"},
    {"id": "page_settings", "label": "Page: Settings", "type": "page", "url": "/dashboard/settings/"},
]
@method_decorator(
    require_full_access(),
    name="dispatch"
)
class DashboardView(LoginRequiredMixin, RequireActivePackageMixin, View):
  def get(self, request, *args, **kwargs):
    invitation, statistics = request.user.get_statistics()
    return render(request, 'dashboard/index.html', {'profile': request.user.profile, 'statistics': statistics, 'invitation': invitation})

  login_url = '/login/'
def build_paytr_iframe(user_ip, user_name, user_address, user_phone, merchant_oid, email, payment_amount, user_basket, no_installment, max_installment, currency, test_mode):

    merchant_key  = settings.MERCHANT_KEY if isinstance(settings.MERCHANT_KEY, bytes) else settings.MERCHANT_KEY.encode()
    merchant_salt = settings.MERCHANT_SALT if isinstance(settings.MERCHANT_SALT, bytes) else settings.MERCHANT_SALT.encode()

    basket = base64.b64encode(
        json.dumps([["Ürün Adı", "1.00", 1]]).encode("utf-8")
    ).decode("utf-8")

    hash_str = (
        settings.MERCHANT_ID
        + user_ip
        + merchant_oid
        + email
        + str(payment_amount)
        + basket
        + no_installment
        + max_installment
        + currency
        + test_mode
    )

    hmac_digest = hmac.new(
        merchant_key,
        hash_str.encode("utf-8") + merchant_salt,
        hashlib.sha256
    ).digest()

    paytr_token = base64.b64encode(hmac_digest).decode("utf-8")

    params = {
        "merchant_id": settings.MERCHANT_ID,
        "user_ip": user_ip,
        "merchant_oid": merchant_oid,
        "email": email,
        "payment_amount": str(payment_amount),
        "user_basket": basket,
        "no_installment": no_installment,
        "max_installment": max_installment,
        "currency": currency,
        "test_mode": test_mode,
        "paytr_token": paytr_token,
        "merchant_ok_url": "https://davetjet.com/subscribe/success",
        "merchant_fail_url": "https://davetjet.com/subscribe/fail",
        "timeout_limit": "30",
        "debug_on": "1",
        "user_name": user_name,
        "user_address": user_address,
        "user_phone": user_phone,
    }

    result = requests.post('https://www.paytr.com/odeme/api/get-token', data=params)
    res = json.loads(result.text)

    if res['status'] == 'success':
        return res['token']  # Bu token'ı iframe içinde kullanabilirsiniz.
        """
        context = {
            'token': res['token']
        }
        """
    else:
        print(result.text, file=sys.stderr)  # Log the error response to stderr for debugging
class HomePageView(TemplateView):
    template_name = "landing/index.html"

    def get(self, request, **kwargs):
        if request.user.is_authenticated:
            pass
        return render(request, self.template_name, {'token': 'token' if request.user.is_authenticated else None})

class SubscribeView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/subscribe.html"
    login_url = 'core:login'

    def get(self, request, **kwargs):
        package = request.user.profile.get_current_package().plan if request.user.profile.get_current_package() else None

        return render(request, self.template_name, {'plans': Plan.objects.all(), 'package': package if package else "Paket Yok",})

class SubscribeFailView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/subscribe-fail.html"
    login_url = 'core:login'

    def get(self, request, **kwargs):
        payment = Payment.objects.filter(user=request.user).order_by('-created_at').first()
        if payment is None:
            return redirect('core:subscribe')
        
        if payment.status != "success":
            return redirect('core:subscribe-next', pk=payment.package.id)

        return render(request, self.template_name, {'payment': payment, 'user': request.user})
class SubscribeSuccessView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/subscribe-success.html"
    login_url = 'core:login'

    def get(self, request, **kwargs):
        payment = Payment.objects.filter(user=request.user).order_by('-created_at').first()
        if payment is None:
            return redirect('core:subscribe')
        
        if payment.status != "success":
            return redirect('core:subscribe-next', pk=payment.package.id)
        
        if request.user.profile.get_current_package() and request.user.profile.get_current_package().plan.id == payment.package.id:
            return render(request, self.template_name, {'payment': payment, 'user': request.user})

        # Attach the package to the user's profile
        request.user.profile.add_new_package(payment.package)

        return render(request, self.template_name, {'payment': payment})

class SubscribeNextView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/subscribe.html"
    login_url = 'core:login'

    def get(self, request, pk, **kwargs):
        old_package = request.user.profile.get_current_package().plan if request.user.profile.get_current_package() else None   
        if old_package and old_package.id == pk:
            return redirect('core:subscribe')
         

        package_obj = get_object_or_404(Plan, id=pk)

        token = build_paytr_iframe(
            user_ip=request.META.get('REMOTE_ADDR', ''),
            user_name=request.user.get_full_name() or request.user.username,
            user_address="NaN",
            user_phone=request.user.phone_number or "NaN",
            merchant_oid = f"{request.user.id}{package_obj.id}{uuid.uuid4().hex[:8]}",
            email=request.user.email,
            payment_amount=int(int(package_obj.price) * 100),  # Ödeme miktarını kuruş cinsinden belirtin (örneğin, 10.00 TL için 1000)
            user_basket=[[f"Davetjet {package_obj.name} Ömür Boyu Erişim", "{{ package_obj.price }}", 1]],
            no_installment="0",
            max_installment="0",
            currency="TRY",
            test_mode="1"  # Gerçek işlem için "0", test işlemi için "1"
        )
        
        # Check if the user has already started payment session
        _payment = Payment.objects.filter(user=request.user, package_id=pk, status="pending").order_by('-created_at').first()
        if _payment:
            return render(request, self.template_name, {'plans': Plan.objects.all(), 'package': old_package if old_package else "Paket Yok", 'token': token})
        
        payment = Payment.objects.create(
            user=request.user,
            package=package_obj,
            merchant_oid=f"{request.user.id}{package_obj.id}{uuid.uuid4().hex[:8]}",
            status="pending",   # henüz ödeme tamamlanmadı
            total_amount=package_obj.price,  
            processed=False
        )
        payment.save()
        #Test
    
        
        return render(request, self.template_name, {'plans': Plan.objects.all(), 'package': old_package if old_package else "Paket Yok", 'token': token})

class PackageView(LoginRequiredMixin, RequireActivePackageMixin, TemplateView):
    template_name = "dashboard/package.html"
    login_url = 'core:login'

    def get(self, request, **kwargs):
        subscription = request.user.profile.get_current_package()

        return render(request, self.template_name, {'subscription': subscription if subscription else "Paket Yok",})

class SearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.GET.get("q", "").strip()
        if not query:
            # Return empty or maybe static commands only
            return Response(STATIC_COMMANDS + STATIC_PAGES)

        # Search invitations by name (case-insensitive)
        invitations = Invitation.objects.filter(name__icontains=query)[:10]
        serialized_invitations = InvitationSerializer(invitations, many=True).data

        # Filter static commands and pages by query inclusion (case-insensitive)
        filtered_commands = [
            cmd for cmd in STATIC_COMMANDS if query.lower() in cmd["label"].lower()
        ]
        filtered_pages = [
            page for page in STATIC_PAGES if query.lower() in page["label"].lower()
        ]

        # Combine all results, prioritizing invitations first, then pages, then commands
        results = serialized_invitations + filtered_pages + filtered_commands

        return Response(results)


class SendingView(LoginRequiredMixin, RequireActivePackageMixin, TemplateView):
    template_name = 'dashboard/sending/sending.html'
    login_url = 'core:login'

    def get(self, request, **kwargs):
        ctx = {}
        invitation, statistics = request.user.get_statistics()
        if not invitation:
            return redirect('core:create-invitation')
        ctx['invitation'] = invitation
        ctx['statistics'] = statistics
        ctx['preview'] = invitation.render_preview_html()
        return render(request, self.template_name, ctx)

class AnalyticsView(LoginRequiredMixin, RequireActivePackageMixin, TemplateView):
    template_name = "dashboard/analytics/analytics.html"
    login_url = 'core:login'

    def get(self, request, **kwargs):
        ctx = {}
        invitation, statistics = request.user.get_statistics()
        if not invitation:
            return redirect('core:create-invitation')
        ctx['invitation'] = invitation
        ctx['statistics'] = statistics
        return render(request, self.template_name, ctx)
class InvitationEditView(RequireActivePackageMixin, TemplateView):
    template_name = "dashboard/invitations/create.html"  # mevcut wizard template'in

    

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        inv = get_object_or_404(Invitation, pk=kwargs["pk"])
        ctx["inv_json"] = json.dumps({
            # temel
            "id": inv.pk,
            "slug": inv.slug,
            "project": inv.project_id,
            "is_draft": inv.is_draft,
            "published_at": inv.published_at.isoformat() if inv.published_at else None,

            "name": inv.name,
            "message": inv.message,
            "invitation_date": inv.invitation_date.isoformat() if inv.invitation_date else None,
            "location": inv.location,

            # şablon
            "template": inv.template,

            # güvenlik
            "is_password_protected": inv.is_password_protected,
            "password": inv.password or "",
            "secure_invite_link": inv.secure_invite_link or "",

            # hatırlatıcılar
            "reminders": inv.reminders,
            "reminder_message": inv.reminder_message,
            "reminder_config": inv.reminder_config,
            "last_reminder_sent": inv.last_reminder_sent.isoformat() if inv.last_reminder_sent else None,
            "max_reminders": inv.max_reminders,
            "reminders_sent": inv.reminders_sent,

            # teslimat/kanallar
            "channels": inv.channels,
            "delivery_settings": inv.delivery_settings,

            # otomasyon
            "automation": inv.automation,
            "retry_count": inv.retry_count,
            "max_retries": inv.max_retries,

            # frontend uyumluluğu için:
            "expires_at": None,              # modelde yok → null geçiyoruz
            "expired": inv.is_expired(),     # durum bilgisi
            "recipients_count": inv.recipients.count(),
        }, cls=DjangoJSONEncoder)
        return ctx