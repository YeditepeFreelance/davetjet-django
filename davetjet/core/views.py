import json
from django.shortcuts import render
from django.views import View
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework.views import APIView
from django.views.generic import TemplateView
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from invitations.models import Invitation
from invitations.serializers import InvitationSerializer

class DashboardView(LoginRequiredMixin, View):
  def get(self, request, *args, **kwargs):
    invitation, statistics = request.user.get_statistics()

    return render(request, 'dashboard/index.html', {'profile': request.user.profile, 'statistics': statistics, 'invitation': invitation})

  login_url = '/login/'

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

class InvitationEditView(TemplateView):
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