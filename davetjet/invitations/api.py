# invitations/api.py  (EK)
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .models import Invitation
from .serializers import InvitationSerializer, InvitationDetailSerializer

@api_view(["GET"])
def list_drafts(request):
    qs = Invitation.objects.filter(is_draft=True).order_by("-id")
    return Response(InvitationSerializer(qs, many=True).data)

@api_view(["POST"])
def promote_draft(request, pk):
    try:
        inv = Invitation.objects.get(pk=pk, is_draft=True)
    except Invitation.DoesNotExist:
        return Response({"error":"Draft not found"}, status=404)

    inv.is_draft = False
    inv.published_at = timezone.now()
    inv.save(update_fields=["is_draft","published_at"])

    # Share link üretimini burada çözüyorsanız ekleyin:
    share_url = getattr(inv, "share_url", None) or f"https://davetjet.com/i/{inv.pk}"
    return Response({"id": inv.pk, "share_url": share_url}, status=200)

@api_view(["DELETE"])
def delete_draft(request, pk):
    try:
        inv = Invitation.objects.get(pk=pk, is_draft=True)
    except Invitation.DoesNotExist:
        return Response(status=404)
    inv.delete()
    return Response(status=204)

WRITEABLE_FIELDS = {
    "name","project","message","invitation_date","location",
    "reminders","reminder_message","reminder_config",
    "channels","delivery_settings",
    "template",
    "is_password_protected","password",
    "is_draft",
}
@api_view(["GET","PATCH"])
def invitation_detail(request, pk):
    try:
        inv = Invitation.objects.get(pk=pk)
    except Invitation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(InvitationDetailSerializer(inv).data)

    data = request.data.copy()

    # Yayında olan kayıtta bazı alanları kilitle
    if not inv.is_draft:
        for f in ["is_draft", "published_at", "template"]:
            data.pop(f, None)

    ser = InvitationDetailSerializer(inv, data=data, partial=True)  # <-- ÖNEMLİ
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)