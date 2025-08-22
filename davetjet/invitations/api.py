# invitations/api.py
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Invitation
from .serializers import InvitationDetailSerializer

# Client tarafının gönderebileceği ama modelde olmayan anahtarlar
CLIENT_ONLY_KEYS = {"expires_at", "share_url", "url", "public_url", "link"}

# Yayınlanmış kayıtta kilitli alanlar
LOCKED_WHEN_PUBLISHED = {"is_draft", "published_at", "template"}

# PATCH ile yazılmasına izin verilen alanlar
WRITEABLE_FIELDS = {
    "name", "project", "message", "invitation_date", "location",
    "reminders", "reminder_message", "reminder_config",
    "channels", "delivery_settings",
    "template",
    "is_password_protected", "password",
    "is_draft",
}

# invitations/api.py
from datetime import timedelta
from collections import defaultdict

from django.utils import timezone
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from invitations.models import Invitation
from recipients.models import Recipient

# --- helpers -----------------------------------------------------------------
def _days_from_range(token: str) -> int:
    return {"7d": 7, "30d": 30, "90d": 90}.get((token or "").lower(), 30)

def _filter_by_channel(qs, ch: str):
    ch = (ch or "all").lower()
    if ch in {"email", "sms", "whatsapp"}:
        key = f"delivery_settings__{ch}"
        qs = qs.filter(Q(**{key: True}) | Q(channels=ch))
    return qs

def _sum_recipients(inv_qs):
    # performanslı toplama için annotate kullan
    return sum(
        row["rc"]
        for row in inv_qs.annotate(rc=Count("recipients")).values("rc")
    )



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_invitation_recipients(request, key):
    """
    key: pk veya slug olabilir.
    /invitations/api/analytics/invitations/<key>/recipients/
    ?status=all|yes|maybe|no|pending&search=
    """
    inv = get_object_or_404(
        Invitation.objects.filter(project__owner=request.user),
        Q(pk__iexact=key) | Q(slug__iexact=key)
    )

    status_filter = (request.GET.get("status") or "all").lower()
    search = (request.GET.get("search") or "").strip()

    qs = Recipient.objects.filter(invitations=inv)
    if status_filter in {"yes", "maybe", "no", "pending"}:
        qs = qs.filter(rsvp_status=status_filter)
    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone_number__icontains=search)
        )

    qs = qs.order_by("name")
    results = [{
        "id": r.id,
        "name": r.name,
        "email": r.email,
        "phone": r.phone_number,
        "status": r.rsvp_status,
        "updated": r.updated_at.isoformat() if r.updated_at else None,
    } for r in qs]

    return Response({"count": len(results), "results": results}, status=200)


def _rsvp_counts_for_invites(inv_qs, since=None):
    """
    RSVP sayıları: Recipient.rsvp_status üzerinden,
    sadece bu davetlere bağlı alıcılar baz alınır.
    Not: RSVP status tüm davetler için tek; projede paylaşım varsa aynı değeri kullanır.
    """
    # ilgili recipient id'lerini topla
    r_ids = set(
        rid for rid in
        Recipient.objects.filter(invitations__in=inv_qs).values_list("id", flat=True)
    )
    if not r_ids:
        return {"yes": 0, "maybe": 0, "no": 0, "rsvped": 0}

    r_qs = Recipient.objects.filter(id__in=r_ids)
    if since is not None:
        r_qs = r_qs.filter(updated_at__gte=since)

    yes = r_qs.filter(rsvp_status="yes").count()
    maybe = r_qs.filter(rsvp_status="maybe").count()
    no = r_qs.filter(rsvp_status="no").count()
    return {"yes": yes, "maybe": maybe, "no": no, "rsvped": yes + maybe + no}

def _timeline(inv_qs, days: int, since):
    """
    Günlük timeline:
      - send: davet.created_at gününde o davetin recipient sayısını ekler (yaklaşık gönderim hacmi)
      - open/click: tracking yoksa 0
      - rsvp: Recipient.updated_at gün sayımları (pending hariç)
    """
    # send: davet oluşturma gününe recipient sayısı yaz
    send_daily = defaultdict(int)
    for row in inv_qs.annotate(rc=Count("recipients")).values("created_at", "rc"):
        d = row["created_at"].date().isoformat()
        send_daily[d] += (row["rc"] or 0)

    # rsvp timeline: recipient.updated_at gününe yaz (pending olmayanlar)
    rsvp_daily = defaultdict(int)
    r_qs = Recipient.objects.filter(invitations__in=inv_qs, updated_at__gte=since) \
                            .exclude(rsvp_status="pending") \
                            .values_list("updated_at", flat=True)
    for ts in r_qs:
        d = ts.date().isoformat()
        rsvp_daily[d] += 1

    days_list = [(since + timedelta(days=i)).date().isoformat() for i in range(days)]
    out = []
    for d in days_list:
        out.append({
            "send": send_daily.get(d, 0),
            "open": 0,     # tracking yoksa 0
            "rsvp": rsvp_daily.get(d, 0),
        })
    return out

# --- API: dropdown için davet listesi ----------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_list_invitations(request):
    """
    /invitations/api/analytics/invitations/
    Kullanıcıya ait davetleri [ {id, name}, ... ] döner.
    """
    qs = Invitation.objects.filter(project__owner=request.user).order_by("-updated_at")
    data = [{"id": inv.id, "name": inv.name} for inv in qs]
    return Response(data, status=200)

# --- API: genel/filtreli overview -------------------------------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_overview(request):
    """
    /invitations/api/analytics/overview/?invitation=all|<id>&channel=all|email|sms|whatsapp&range=7d|30d|90d
    UI'nin beklediği: { totals, channels, timeline, top }
    """
    inv_param = request.GET.get("invitation", "all")
    ch_param  = request.GET.get("channel", "all")
    rng       = request.GET.get("range", "30d")

    days  = _days_from_range(rng)
    now   = timezone.now()
    since = now - timedelta(days=days)

    # kapsam: kullanıcıya ait davetler
    qs = Invitation.objects.filter(project__owner=request.user, created_at__gte=since)
    if inv_param != "all":
        try:
            qs = qs.filter(pk=int(inv_param))
        except ValueError:
            qs = qs.none()

    qs = _filter_by_channel(qs, ch_param)

    # totals
    total_invites = qs.count()
    delivered = _sum_recipients(qs)
    rsvp_counts = _rsvp_counts_for_invites(qs, since=since)
    yes, maybe, no = rsvp_counts["yes"], rsvp_counts["maybe"], rsvp_counts["no"]
    rsvped = rsvp_counts["rsvped"]

    # channels: gönderim hacmi yaklaşımı (ilgili davetlerin recipient toplamı)
    q_email = _filter_by_channel(qs, "email")
    q_sms   = _filter_by_channel(qs, "sms")
    q_wa    = _filter_by_channel(qs, "whatsapp")
    ch_email = _sum_recipients(q_email)
    ch_sms   = _sum_recipients(q_sms)
    ch_wa    = _sum_recipients(q_wa)

    # timeline
    timeline = _timeline(qs, days, since)

    # top invites (en çok gönderim – recipient sayısı)
    top = []
    for row in qs.annotate(rc=Count("recipients")).values("id","name","rc","updated_at"):
        top.append({
            "name": row["name"],
            "sent": row["rc"] or 0,
            "opened": 0,                    # tracking yoksa 0
            "rsvp": 0 if not rsvped else None,  # istersen burayı per-inv hesaplayabiliriz (aşağıda not)
            "updated": row["updated_at"].strftime("%d.%m.%Y %H:%M") if row["updated_at"] else "",
            "url": f"/dashboard/invitations/{row['id']}/",
        })
    top.sort(key=lambda r: r["sent"], reverse=True)
    top = top[:10]

    return Response({
        "totals": {
            "total": total_invites,
            "delivered": delivered,
            "bounces": 0,
            "opened": 0,
            "clicked": 0,
            "rsvped": rsvped,
            "yes": yes, "maybe": maybe, "no": no,
        },
        "channels": {
            "email": ch_email, "sms": ch_sms, "whatsapp": ch_wa
        },
        "timeline": timeline,
        "top": top,
    }, status=200)

# --- API: tek davetiye detay (RSVP dağılımı + kısmi timeline) ----------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_invitation_detail(request, pk):
    """
    /invitations/api/analytics/invitations/<pk>/?range=7d|30d|90d
    Tek davetiye için RSVP dağılımı ve mini timeline
    """
    inv = get_object_or_404(Invitation, pk=pk, project__owner=request.user)
    rng  = request.GET.get("range", "30d")
    days = _days_from_range(rng)
    since = timezone.now() - timedelta(days=days)

    qs = Invitation.objects.filter(pk=pk)
    rsvp_counts = _rsvp_counts_for_invites(qs, since=since)
    timeline = _timeline(qs, days, since)

    return Response({
        "invitation": {"id": inv.id, "name": inv.name},
        "rsvp": rsvp_counts,      # { yes, maybe, no, rsvped }
        "timeline": timeline,     # [{send, open, rsvp}, ...]
    }, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_drafts(request):
    """
    Taslakları listele – message dahil döndür (UI tarafında mesaj görünmüyorsa sebebi buydu).
    """
    qs = Invitation.objects.filter(is_draft=True).order_by("-id")
    out = []
    for inv in qs:
        out.append({
            "id": inv.pk,
            "name": inv.name,
            "template": inv.template,
            "invitation_date": inv.invitation_date.isoformat() if inv.invitation_date else None,
            "is_draft": inv.is_draft,
            "message": inv.message or "",
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "updated_at": inv.updated_at.isoformat() if inv.updated_at else None,
        })
    return Response(out, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def promote_draft(request, pk):
    """
    Taslağı yayınla (idempotent).
    """
    inv = get_object_or_404(Invitation, pk=pk)
    if not inv.is_draft:
        share_url = getattr(inv, "secure_invite_link", None) or f"https://davetjet.com/i/{inv.slug}"
        return Response({"id": inv.pk, "share_url": share_url, "already_published": True}, status=200)

    inv.is_draft = False
    inv.published_at = timezone.now()
    inv.save(update_fields=["is_draft", "published_at", "updated_at"])

    share_url = getattr(inv, "secure_invite_link", None) or f"https://davetjet.com/i/{inv.slug}"
    return Response({"id": inv.pk, "share_url": share_url}, status=200)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_draft(request, pk):
    inv = get_object_or_404(Invitation, pk=pk, is_draft=True)
    inv.delete()
    return Response(status=204)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def invitation_detail(request, pk):
    inv = get_object_or_404(Invitation, pk=pk)

    if request.method == "GET":
        return Response(InvitationDetailSerializer(inv).data, status=200)

    # ---- PATCH ----
    data = request.data
    if hasattr(data, "dict"):   # QueryDict ise düz sözlük yap
        data = data.dict()

    # Client-only anahtarları at
    for k in list(data.keys()):
        if k in CLIENT_ONLY_KEYS:
            data.pop(k, None)

    # Sadece izin verilen alanları bırak
    data = {k: v for k, v in data.items() if k in WRITEABLE_FIELDS}

    # Yayında kilitli alanları at
    if not inv.is_draft:
        for f in LOCKED_WHEN_PUBLISHED:
            data.pop(f, None)

    # DEBUG (isteğe bağlı): print(f"[PATCH Invitation {inv.pk}] incoming:", data)

    ser = InvitationDetailSerializer(inv, data=data, partial=True)
    if not ser.is_valid():
        return Response(ser.errors, status=400)

    inv = ser.save()
    inv.refresh_from_db()

    return Response(InvitationDetailSerializer(inv).data, status=200)
# views.py (ilgili importlar yoksa ekleyin)
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def schedule_send(request, pk):
    """
    /invitations/api/schedule-send/<pk>/
    - being_sent=True -> save()  (sinyaller yalnızca bu flag açıkken çalışacak)
    - seçilen kanallar ve kanal bazlı içerik (email/sms) delivery_settings'e yazılır
    - iş biter bitmez being_sent=False yapılır
    """
    def _truthy(v):  # checkbox/string normalize
        return str(v).lower() in ("1", "true", "on", "yes")

    def _clean(s):
        return (s or "").strip()

    with transaction.atomic():
        inv = get_object_or_404(
            Invitation.objects.select_for_update().select_related("project"),
            pk=pk,
            project__owner=request.user,
        )

        data = request.data if isinstance(request.data, dict) else {}

        # --- Kanallar ---
        ds = (inv.delivery_settings or {}).copy()
        ch = data.get("channels")
        if isinstance(ch, dict):
            ds["email"]    = bool(ch.get("email",    ds.get("email", True)))
            ds["sms"]      = bool(ch.get("sms",      ds.get("sms", False)))
            ds["whatsapp"] = bool(ch.get("whatsapp", ds.get("whatsapp", False)))
        else:
            if "channel_email" in data:    ds["email"]    = _truthy(data.get("channel_email"))
            if "channel_sms" in data:      ds["sms"]      = _truthy(data.get("channel_sms"))
            if "channel_whatsapp" in data: ds["whatsapp"] = _truthy(data.get("channel_whatsapp"))

        # --- İçerikler (frontend'den gelenleri kullan; yoksa fallback) ---
        general_message = _clean(data.get("message") or inv.message or "")
        email_message   = _clean(data.get("email_message") or general_message)
        sms_message     = _clean(data.get("sms_message")   or general_message)
        email_subject   = _clean(data.get("email_subject") or f"{inv.name} — Davetiye")

        # Pretty davetiye URL'si (sinyaller için faydalı)

        # Kanala göre boşalt (aktif olmayan kanala içerik taşımayalım)
        ds["content"] = {
            "general": general_message,
            "email":   email_message if ds.get("email") else "",
            "sms":     sms_message   if ds.get("sms")   else "",
            "email_subject": email_subject,
        }

        # --- Zamanlama ---
        schedule = data.get("schedule") or {}
        mode = (schedule.get("mode") or "now").lower()
        when_iso = schedule.get("scheduled_at")
        when_dt = None
        if when_iso:
            when_dt = parse_datetime(when_iso)
            if when_dt and timezone.is_naive(when_dt):
                when_dt = timezone.make_aware(when_dt, timezone.get_current_timezone())

        ds["schedule"] = {
            "mode": mode,                              # "now" | "later"
            "scheduled_at": when_dt.isoformat() if when_dt else None,  # ISO8601 veya None
        }

        # --- Davetiye state ---
        inv.delivery_settings = ds
        inv.being_sent = True

        # Taslaktaysa yayınla (opsiyonel ama genelde gerekli)
        if inv.is_draft:
            inv.is_draft = False
            if not inv.published_at:
                inv.published_at = timezone.now()

        # Kritik save: sinyaller burada tetiklenir (being_sent=True)
        inv.save()

    # Sinyaller kurulumunu yaptı; flag'i kapat
    inv.being_sent = False
    inv.save(update_fields=["being_sent"])

    return Response(
        {
            "ok": True,
            "message": "Gönderim planlaması başlatıldı. Seçilen kanallara göre iletilecek.",
            "invitation_id": inv.id,
            "channels": inv.delivery_settings.get("channels") or {
                "email": inv.delivery_settings.get("email", False),
                "sms": inv.delivery_settings.get("sms", False),
                "whatsapp": inv.delivery_settings.get("whatsapp", False),
            },
            "content": inv.delivery_settings.get("content", {}),
            "schedule": inv.delivery_settings.get("schedule", {}),
            "is_draft": inv.is_draft,
        },
        status=status.HTTP_200_OK,
    )
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Invitation
class InvitationSnapshotUpload(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        inv = get_object_or_404(
            Invitation.objects.select_related('project'),
            pk=pk, project__owner=request.user
        )
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "file is required"}, status=400)
        inv.snapshot_image.save(file.name, file, save=True)
        return Response({"url": inv.snapshot_image.url}, status=200)
