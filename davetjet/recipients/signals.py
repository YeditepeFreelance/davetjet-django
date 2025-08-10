# recipients/signals.py
from datetime import timedelta
import re

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone

from recipients.models import Recipient
from invitations.models import Invitation
from invitations.utils import render_invitation_html  # <- utils'e taşındı
from communication.scheduler import SchedulerService

scheduler = SchedulerService()


def _normalize_phone(raw: str) -> str | None:
    """
    Basit normalize:
    - Rakam dışını temizler
    - Başta 0'ı kırpar
    - +90 prefiksi yoksa ekler
    """
    if not raw:
        return None
    digits = re.sub(r"\D+", "", raw)
    if not digits:
        return None
    if digits.startswith("0"):
        digits = digits[1:]
    if digits.startswith("90"):
        return f"+{digits}"
    if not digits.startswith("+"):
        return f"+90{digits}"
    return digits


def _build_sms_text(invitation: Invitation, recipient: Recipient | None = None) -> str:
    dt = invitation.invitation_date
    date_str = dt.strftime("%d.%m.%Y") if dt else ""
    time_str = dt.strftime("%H:%M") if dt else ""
    loc = getattr(invitation, "location", "") or ""
    lines = [
        invitation.name or "Davet",
        f"{date_str} {time_str}".strip(),
        loc,
    ]
    msg = (invitation.message or "").strip()
    if msg:
        lines.append(msg)
    return "\n".join([l for l in lines if l]).strip()


def _can_send(inv: Invitation) -> bool:
    """Taslak değil + tarihi var + henüz geçmemiş olmalı."""
    return (not inv.is_draft) and bool(inv.invitation_date) and (not inv.is_expired())


@receiver(post_save, sender=Recipient)
def resend_invitation_to_updated_recipient(sender, instance: Recipient, **kwargs):
    """
    Recipient güncellendiğinde ilgili yayınlanmış davetiyeleri yeniden planla.
    - Taslaklar asla gönderilmez.
    - 5 dk throttle (aynı pair için).
    - teslim kanalları delivery_settings'e göre kontrol edilir.
    """
    # RelatedManager'da custom manager yok; doğrudan filtrele
    invitations = instance.invitations.filter(is_draft=False)
    if not invitations.exists():
        return

    for invitation in invitations:
        if not _can_send(invitation):
            continue

        # throttle: 5 dk içinde tekrar etme
        throttle_key = f"resend_inv:{invitation.pk}:{instance.pk}"
        if not cache.add(throttle_key, 1, timeout=300):
            continue

        try:
            # Kanallar
            delivery = (invitation.delivery_settings or {})  # {'email': True, 'sms': False, ...}
            email_allowed = delivery.get("email", True)
            sms_allowed = delivery.get("sms", False)

            # E-POSTA
            if email_allowed and instance.email:
                html_content = render_invitation_html(invitation)
                scheduler.schedule_email(
                    recipients=[instance.email],
                    send_time=timezone.now() + timedelta(seconds=10),
                    subject=f"{invitation.name} Davetiyesi (Güncel)",
                    message="",                # plain text opsiyonel
                    html_message=html_content, # esas gövde
                )

            # SMS (opsiyonel)
            if sms_allowed:
                phone_raw = getattr(instance, "phone", None) or getattr(instance, "gsm", None)
                phone = _normalize_phone(phone_raw)
                if phone:
                    sms_text = _build_sms_text(invitation, instance)
                    # SchedulerService'te schedule_sms varsa:
                    if hasattr(scheduler, "schedule_sms"):
                        scheduler.schedule_sms(
                            recipients=[phone],
                            send_time=timezone.now() + timedelta(seconds=10),
                            message=sms_text,
                        )

        except Exception as e:
            # prod'da logger kullan; örnek basit çıktı:
            print(f"[SIGNAL ERROR] Recipient:{instance.pk} Invitation:{invitation.pk} -> {e}")
