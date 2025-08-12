# signals.py
import re
import logging
from datetime import timedelta
from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache
from django.utils.html import escape
from django.conf import settings

from .models import Invitation
from .utils import render_invitation_html
from communication.scheduler import EnhancedSchedulerService

log = logging.getLogger(__name__)

scheduler = EnhancedSchedulerService(
    sms_username=settings.NETGSM_USERNAME,
    sms_password=settings.NETGSM_PASSWORD,
    msgheader=getattr(settings, "NETGSM_APPNAME", None)
)

# ---------- helpers ----------
def _normalize_tr_phone(msisdn: str | None) -> str | None:
    """Netgsm 'no' için 10 haneli TR GSM: 5XXXXXXXXX"""
    if not msisdn:
        return None
    digits = re.sub(r"\D+", "", msisdn)
    if not digits:
        return None
    if digits.startswith("90") and len(digits) >= 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) >= 11:
        digits = digits[1:]
    if len(digits) == 10 and digits.startswith("5"):
        return digits
    if len(digits) > 10 and digits[-10:].startswith("5"):
        return digits[-10:]
    return None

def _can_send(inv: Invitation) -> bool:
    ok = (not inv.is_draft) and bool(inv.invitation_date) and (not inv.is_expired())
    log.debug(
        "can_send? inv=%s is_draft=%s date=%s expired=%s -> %s",
        inv.pk, inv.is_draft, inv.invitation_date, inv.is_expired(), ok
    )
    return ok

def _format_msg_html(text: str | None) -> str:
    if not text:
        return ""
    return escape(text).replace("\n", "<br>")

def _compose_invitation_email_html(inv: Invitation) -> str:
    # Marka yeşilleri
    primary = "#2b8556"
    primary_dark = "#1f6f46"

    msg_html = _format_msg_html((inv.message or "").strip())
    link = (inv.secure_invite_link or "").strip()
    preview_html = render_invitation_html(inv)

    cta_html = ""
    if link:
        cta_html = f"""
          <div style="margin:16px 0 8px;">
            <a href="{link}"
               style="display:inline-block;padding:12px 18px;border-radius:10px;
                      background:{primary};color:#ffffff;text-decoration:none;
                      font-weight:700;font-family:Inter,Segoe UI,Arial,sans-serif;"
               target="_blank" rel="noopener">
              Davetiyeyi açın
            </a>
          </div>
          <div style="font-size:12px;color:#667085;margin-bottom:20px;">
            Link çalışmazsa butona tekrar tıklayın.
          </div>
        """

    return f"""
    <div style="max-width:680px;margin:0 auto;padding:20px;background:#ffffff;">
      {'<div style="margin-bottom:12px;line-height:1.6;color:#1F2937;">' + msg_html + '</div>' if msg_html else '' }
      {cta_html}
      <hr style="border:none;border-top:1px solid #eee;margin:20px 0;" />
      <div style="border-radius:12px;overflow:hidden;border:1px solid #eee;">
        {preview_html}
      </div>
      {'<div style="text-align:center;margin-top:18px;"><a href="' + link + '" target="_blank" rel="noopener" style="color:'+ primary_dark +';text-decoration:underline;font-weight:600;">Davetiyeyi yeni sekmede aç</a></div>' if link else ''}
    </div>
    """

def _compose_sms_text(inv: Invitation) -> str:
    """TR formatlı, okunur SMS gövdesi"""
    dt = inv.invitation_date
    date_str = time_str = ""
    if dt:
        dt = timezone.localtime(dt)
        date_str = dt.strftime("%d.%m.%Y")
        time_str = dt.strftime("%H:%M")

    name = (inv.name or "").strip()
    loc  = (inv.location or "").strip()
    msg  = (inv.message or "").strip()
    link = (inv.secure_invite_link or "").strip()

    lines = []
    if name:
        lines.append(name)
    if date_str or time_str:
        lines.append(f"Tarih: {date_str}  Saat: {time_str}".strip())
    if loc:
        lines.append(f"Mekan: {loc}")
    if msg:
        lines.append(msg)
    if link:
        lines.append(f"Bağlantı: {link}")

    text = "\n".join(lines).strip()
    return text[:918]  # güvenli kırpma (~6 SMS)

def _send_email_batch(inv: Invitation, emails: list[str]):
    if not emails:
        log.debug("email skip: empty recipient list")
        return
    html_content = _compose_invitation_email_html(inv)
    run_at = timezone.now() + timedelta(seconds=10)
    log.info("Scheduling email: count=%s run_at=%s inv_id=%s", len(emails), run_at, inv.pk)
    scheduler.schedule_email(
        recipients=emails,
        send_time=run_at,
        subject=f"{inv.name} Davetiyesi",
        message="",
        html_message=html_content,
    )

def _send_sms_batch(inv: Invitation, recipients_qs):
    phones = []
    sms_text = _compose_sms_text(inv)
    for phone_raw in recipients_qs.values_list("phone_number", flat=True):
        p = _normalize_tr_phone(phone_raw)
        if p:
            phones.append(p)
    if not phones:
        log.debug("sms skip: empty phones")
        return
    run_at = timezone.now() + timedelta(seconds=10)
    log.info("Scheduling SMS: count=%s run_at=%s inv_id=%s", len(phones), run_at, inv.pk)
    scheduler.schedule_sms(
        recipients=phones,
        message=sms_text,
        header=getattr(settings, "NETGSM_APPNAME", None),
        send_time=run_at,
    )

def _burst_lock(key: str, ttl: int = 30) -> bool:
    ok = cache.add(key, "1", timeout=ttl)
    log.debug("lock %s -> %s", key, ok)
    return ok

# ---------- REMINDERS ----------
def _compose_reminder_email_html(inv: Invitation) -> str:
    """Hatırlatma maili: üstte kısa başlık + CTA + özet + preview."""
    primary = "#2b8556"
    link = (inv.secure_invite_link or "").strip()
    top = f"""
      <h2 style="margin:0 0 12px 0;color:#0f172a;font-family:Inter,Segoe UI,Arial,sans-serif;">
        Etkinlik Hatırlatması: {escape(inv.name or '')}
      </h2>
      <p style="margin:0 0 12px 0;color:#334155;">
        Etkinlik yaklaşıyor, detayları aşağıda bulabilirsiniz.
      </p>
    """
    return top + _compose_invitation_email_html(inv)

def _get_owner_and_quota(inv: Invitation):
    """
    Opsiyonel: kullanıcı hatırlatma kredisi.
    Kullanıcı/profilinde şu alanlardan biri varsa kullan: reminder_credits / reminder_quota / remaining_reminders
    Yoksa None döner ve quota kontrolü yapılmaz.
    """
    user = getattr(inv.project, "owner", None)
    profile = getattr(user, "profile", None)
    if not profile:
        return None, None, None
    for field in ("reminder_credits", "reminder_quota", "remaining_reminders"):
        if hasattr(profile, field):
            return user, profile, field
    return user, None, None

def _consume_quota_if_any(inv: Invitation, needed: int) -> bool:
    """
    needed: planlanan reminder job sayısı (batch bazlı). 
    Eğer krediyi kişi başına saymak istersen: needed *= recipient_sayisi
    """
    user, profile, field = _get_owner_and_quota(inv)
    if not profile or not field:
        return True  # quota yok, serbest
    current = getattr(profile, field, 0) or 0
    if current < needed:
        log.warning("Insufficient reminder quota: have=%s need=%s", current, needed)
        return False
    setattr(profile, field, current - needed)
    profile.save(update_fields=[field])
    log.info("Reminder quota consumed: -%s -> %s", needed, current - needed)
    return True

def schedule_reminders_for_invitation(inv: Invitation):
    """
    reminder_config (dakika önce) değerlerine göre İLERİ tarihli hatırlatma e-posta + SMS planla.
    Çift planlamayı önlemek için cache lock + job-id key mantığı.
    """
    if not inv.reminders:
        log.debug("reminders off -> skip")
        return
    if not _can_send(inv):
        log.debug("reminders skip: can_send=False")
        return

    # Bir kez çalışsın (ör. publish anı)
    if not _burst_lock(f"inv:{inv.pk}:rem_sched", ttl=30):
        log.debug("reminders skip: locked")
        return

    now = timezone.now()
    cfg = inv.reminder_config or [1440, 60, 30]
    # int, >0, tekrar yok
    try:
        offsets = sorted({int(x) for x in cfg if int(x) > 0}, reverse=True)
    except Exception:
        offsets = [1440, 60, 30]

    # Alıcı listelerini çıkar (o anki liste)
    emails = [e for e in inv.recipients.values_list("email", flat=True) if e]
    phones = []
    for raw in inv.recipients.values_list("phone_number", flat=True):
        p = _normalize_tr_phone(raw)
        if p:
            phones.append(p)

    # Kaç reminder job planlanacak? (sadece ileri tarihli olanlar)
    future_offsets = []
    for m in offsets:
        run_at = inv.invitation_date - timedelta(minutes=m)
        if run_at > now:
            future_offsets.append(m)

    if not future_offsets:
        log.info("No future reminder offsets to schedule.")
        return

    # (Opsiyonel) kredi tüket
    # kişi başına saymak istersen: needed = len(future_offsets) * max(len(emails), len(phones))
    needed = len(future_offsets)
    if not _consume_quota_if_any(inv, needed):
        log.warning("Reminder scheduling skipped due to quota.")
        return

    subj = f"Hatırlatma: {inv.name}"
    html = _compose_reminder_email_html(inv)
    sms_text = _compose_sms_text(inv)
    header = getattr(settings, "NETGSM_APPNAME", None)

    for m in future_offsets:
        run_at = inv.invitation_date - timedelta(minutes=m)
        # email
        if emails:
            scheduler.schedule_email(
                recipients=emails,
                send_time=run_at,
                subject=subj,
                message="",          # istersen plain text ekle
                html_message=html,
            )
        # sms
        if phones:
            scheduler.schedule_sms(
                recipients=phones,
                message=sms_text,
                header=header,
                send_time=run_at,
            )
        log.info("Reminder scheduled: inv=%s offset_min=%s run_at=%s emails=%s phones=%s",
                 inv.pk, m, run_at, len(emails), len(phones))

# ---------- publish transition guard ----------
@receiver(pre_save, sender=Invitation)
def _remember_draft_state(sender, instance: Invitation, **kwargs):
    instance._was_draft = True
    if instance.pk:
        try:
            old = Invitation.objects.get(pk=instance.pk)
            instance._was_draft = old.is_draft
        except Invitation.DoesNotExist:
            pass

@receiver(post_save, sender=Invitation)
def invitation_published_send_all(sender, instance: Invitation, created, **kwargs):
    # sadece "taslaktan → yayında" geçişinde toplu gönder
    if created:
        log.debug("post_save(created=True) skip")
        return
    if not _can_send(instance):
        log.debug("post_save skip: can_send=False")
        return
    if not getattr(instance, "_was_draft", True):
        log.debug("post_save skip: not a draft->published transition")
        return

    # tek seferlik dispatch (m2m ile çakışmayı azaltır)
    if not _burst_lock(f"inv:{instance.pk}:dispatch", ttl=30):
        log.debug("post_save skip: locked")
        return

    all_recs = instance.recipients.all()

    # her iki kanalı da dene (bilgisi olanlara gider)
    emails = [e for e in all_recs.values_list("email", flat=True) if e]
    log.debug("post_save emails=%s", emails)
    _send_email_batch(instance, emails)
    _send_sms_batch(instance, all_recs)

    # >>> HATIRLATICILARI BURADA PLANLA <<<
    schedule_reminders_for_invitation(instance)

@receiver(m2m_changed, sender=Invitation.recipients.through)
def invitation_recipients_changed(sender, instance: Invitation, action, pk_set, **kwargs):
    log.debug("m2m_changed action=%s inv_id=%s pk_set=%s", action, instance.pk, pk_set)

    if action != "post_add":
        log.debug("m2m skip: action!=post_add")
        return
    if not _can_send(instance):
        log.debug("m2m skip: can_send=False (is_draft or expired or no date)")
        return
    if not pk_set:
        log.debug("m2m skip: empty pk_set")
        return

    # m2m için pk_set’e özel lock — publish ile çakışmayı azaltır
    lock_key = f"inv:{instance.pk}:m2m:{hash(frozenset(pk_set))}"
    if not _burst_lock(lock_key, ttl=15):
        log.debug("m2m skip: locked")
        return

    added_qs = instance.recipients.filter(pk__in=pk_set)

    # her iki kanal
    emails = [e for e in added_qs.values_list("email", flat=True) if e]
    log.debug("m2m emails=%s", emails)
    _send_email_batch(instance, emails)
    _send_sms_batch(instance, added_qs)
