import re 
import sys
from bs4 import BeautifulSoup, NavigableString
from datetime import datetime, timedelta
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.conf import settings
from .utils import render_invitation_html  # <- utils'e taşındı
import os

from .models import Invitation
from datetime import timezone

import requests
from xml.etree.ElementTree import Element, SubElement, tostring

from django.conf import settings
from communication.scheduler import EnhancedSchedulerService

scheduler = EnhancedSchedulerService(
    sms_username=settings.NETGSM_USERNAME,
    sms_password=settings.NETGSM_PASSWORD,
    msgheader=settings.NETGSM_APPNAME
)
# print(scheduler.send_sms_now(["5465952986"], message="Test mesajı"), file=sys.stdout)
def schedule_reminders(self):
    times = self.reminder_config or [1440, 60, 30]  # dakika
    for minutes_before in times:
        if self.reminders_sent >= self.max_reminders:
            break

        send_time = self.invitation_date - timedelta(minutes=minutes_before)

        # Mail gönder
        scheduler.schedule_email(
            recipients=self.recipients.values_list('email', flat=True),
            send_time=send_time,
            subject=f"Reminder: {self.name}",
            message=self.reminder_message or self.message,
            callback=self.update_last_reminder_sent
        )

        # SMS gönder
        scheduler.schedule_sms(
            recipients=list(self.recipients.values_list('phone', flat=True)),
            send_time=send_time,
            message=self.reminder_message or self.message
        )

        self.reminders_sent += 1
    self.save(update_fields=['reminders_sent'])

def _normalize_phone(raw: str) -> str | None:
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


def _can_send(inv: Invitation) -> bool:
    return (not inv.is_draft) and bool(inv.invitation_date) and (not inv.is_expired())


@receiver(m2m_changed, sender=Invitation.recipients.through)
def send_invitation_to_new_recipients(sender, instance: Invitation, action, pk_set, **kwargs):
    """
    Davetiyeye yeni alıcı eklendiğinde ilk gönderimi planla.
    - Yalnızca yayınlanmış ve geçerli davetiyelerde çalışır.
    - delivery_settings'e göre kanal seçimi.
    """
    if action != "post_add":
        return
    if not _can_send(instance):
        return

    delivery = instance.delivery_settings or {}
    email_allowed = delivery.get("email", True)
    sms_allowed = delivery.get("sms", False)

    # Hedef alıcılar
    recipients_qs = instance.recipients.filter(pk__in=pk_set)

    # E-POSTA
    if email_allowed:
        emails = list(recipients_qs.values_list("email", flat=True))
        if emails:
            html_content = render_invitation_html(instance)
            scheduler.schedule_email(
                recipients=emails,
                send_time=timezone.now() + timedelta(seconds=10),
                subject=f"{instance.name} Davetiyesi",
                message="",                # plain text opsiyonel
                html_message=html_content,
            )

    # SMS (opsiyonel)
    if sms_allowed and hasattr(scheduler, "schedule_sms"):
        phones = []
        for phone_raw in recipients_qs.values_list("phone", flat=True):
            p = _normalize_phone(phone_raw)
            if p:
                phones.append(p)
        if phones:
            # Kısa metin
            dt = instance.invitation_date
            date_str = dt.strftime("%d.%m.%Y") if dt else ""
            time_str = dt.strftime("%H:%M") if dt else ""
            loc = getattr(instance, "location", "") or ""
            sms_text = "\n".join([v for v in [instance.name, f"{date_str} {time_str}".strip(), loc, (instance.message or "").strip()] if v]).strip()

            scheduler.schedule_sms(
                recipients=phones,
                send_time=timezone.now() + timedelta(seconds=10),
                message=sms_text,
            )
