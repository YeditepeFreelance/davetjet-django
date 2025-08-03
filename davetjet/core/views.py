from django.shortcuts import render
from django.views import View
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from invitations.models import Invitation
from invitations.serializers import InvitationSerializer

class DashboardView(LoginRequiredMixin, View):
  def get(self, request, *args, **kwargs):
    statistics = request.user.get_statistics()

    return render(request, 'dashboard/index.html', {'profile': request.user.profile, 'statistics': statistics})

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