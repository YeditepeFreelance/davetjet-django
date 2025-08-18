import os
import uuid
from datetime import timedelta
from bs4 import BeautifulSoup, NavigableString
from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.utils.functional import cached_property
from django.db.models import JSONField
from django.core.exceptions import ValidationError
from django.conf import settings

from communication.scheduler import SchedulerService
from davetjet.config import channel_choices
from .utils import generate_secure_invitation_link
from django.template.loader import render_to_string

# KREDİ yardımcıları
from users.credits import get_reminder_credits, consume_reminder_credits

scheduler = SchedulerService()

# --- CONSTANTS ---
TEMPLATE_CHOICES = [
    ('classic', 'Classic'),
    ('modern', 'Modern'),
    ('minimal', 'Minimal'),
]

TEMPLATE_MAP = {
    "classic": "inv-temps/classic.html",
    "modern":  "inv-temps/modern.html",
    "minimal": "inv-temps/minimal.html",
}

class Invitation(models.Model):
    """
    Main Invitation model.
    Handles recipients, reminders, security, and delivery settings.
    """

    # --- BASIC INFO ---
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, help_text="Unique identifier for the invitation.")
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='invitation',
        help_text='The project associated with this invitation.'
    )

    # --- CONTENT ---
    message = models.TextField(blank=True, help_text="Main invitation message.")
    invitation_date = models.DateTimeField(help_text="Event date and time.")
    location = models.CharField(max_length=255, blank=True, help_text="Optional location of the event.")

    # --- RECIPIENTS ---
    recipients = models.ManyToManyField(
        'recipients.Recipient',
        related_name='invitations',
        blank=True,
        help_text='Recipients who can accept this invitation.'
    )

    # --- REMINDERS ---
    reminders = models.BooleanField(default=False, help_text="Enable or disable reminders.")
    reminder_message = models.TextField(blank=True, help_text="Custom message for reminders.")
    reminder_config = JSONField(
        default=list,
        blank=True,
        help_text="List of reminder times in minutes before event. Example: [1440, 60, 30]"
    )
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    max_reminders = models.PositiveIntegerField(default=3, help_text="Max number of reminders allowed by plan.")
    reminders_sent = models.PositiveIntegerField(default=0, help_text="How many reminders have been sent.")

    # --- DELIVERY SETTINGS ---
    channels = models.CharField(
        max_length=10,
        choices=channel_choices,
        default='email',
        help_text='Default sending channel for invitations.'
    )
    delivery_settings = JSONField(
        default=dict,
        blank=True,
        help_text="Custom delivery settings: {'email': True, 'sms': True, 'whatsapp': False}"
    )

    # --- TEMPLATE ---
    template = models.CharField(
        max_length=50,
        choices=TEMPLATE_CHOICES,
        default='classic',
        verbose_name='Template'
    )

    # --- SECURITY ---
    is_password_protected = models.BooleanField(default=True)
    password = models.CharField(max_length=100, blank=True)
    secure_invite_link = models.URLField(max_length=300, blank=True)

    # --- AUTOMATION ---
    automation = models.BooleanField(default=False, help_text="Automation enabled?")
    retry_count = models.PositiveIntegerField(default=0, help_text="Retry count for unanswered reminders.")
    max_retries = models.PositiveIntegerField(default=1, help_text="Max retries for unanswered reminders.")

    # --- META ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_draft = models.BooleanField(default=True, db_index=True)
    is_locked = models.BooleanField(default=False, db_index=True)  # <— NEW
    published_at = models.DateTimeField(null=True, blank=True)  # EK
    being_sent = models.BooleanField(default=False, db_index=True)

    class Published(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(is_draft=False)

    objects = models.Manager()
    published = Published()

    def __str__(self):
        return self.name

    @cached_property
    def is_ready(self) -> bool:
        """UI için: alanlar tamam mı? (gönderilmiş/kilitli olması şart değil)"""
        required_filled = bool(self.name and self.invitation_date and self.template and self.message)
        # istersen location/message da zorunlu kıl:
        # required_filled = required_filled and bool(self.message) and bool(self.location)
        return required_filled

    @property
    def status_label(self) -> str:
        if self.is_locked:
            return "Gönderildi"
        if self.is_ready:
            return "Hazır"
        return "Taslak"

    def lock_after_send(self):
        """Gönderimden sonra çağrılır."""
        self.is_draft = False
        self.is_locked = True
        if not self.published_at:
            self.published_at = timezone.now()
        self.save(update_fields=["is_draft","is_locked","published_at","updated_at"])

    @property
    def can_send(self) -> bool:
        """Gönderim/schedule yapılabilir mi?"""
        return (not self.is_draft) and (self.invitation_date is not None) and (not self.is_expired())

    @cached_property
    def preview_template_path(self) -> str:
        return TEMPLATE_MAP.get(self.template, "inv-temps/classic.html")

    def render_preview_html(self, *, strip_scripts: bool = False, prefer_secure_link: bool = True) -> str:
        """
        Statik şablonu okuyup davetiye alanlarıyla doldurur ve tek bir HTML string döndürür.
        - strip_scripts=True -> <script> etiketlerini kaldırır (e-posta için)
        - prefer_secure_link=True -> varsa secure_invite_link'i, yoksa /invitations/<slug>/ kullanır
        """
        # 1) Şablonu yükle
        rel = self.preview_template_path  # örn: "inv-temps/classic.html"
        template_path = os.path.join(settings.BASE_DIR, "static", rel)
        if not os.path.exists(template_path):
            return '<div style="padding:12px;color:#b91c1c">Şablon bulunamadı.</div>'

        with open(template_path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # --- küçük yardımcılar ---
        def _set_text(el, value: str | None):
            el.clear()
            el.append(NavigableString("" if value is None else str(value)))

        def _set_attr(el, attr, value: str | None):
            if value is None:
                if attr in el.attrs:
                    del el[attr]
            else:
                el[attr] = str(value)

        def _ensure_el(selector: str, tag_name="span"):
            el = soup.select_one(selector)
            if el is None:
                parent = soup.body or soup
                el = soup.new_tag(tag_name)
                if selector.startswith("#"):
                    el["id"] = selector[1:]
                parent.append(el)
            return el

        # 2) Alanları doldur
        dt = self.invitation_date
        if dt:
            dt = timezone.localtime(dt)
            date_str = dt.strftime("%d.%m.%Y")
            time_str = dt.strftime("%H:%M")
        else:
            date_str = ""
            time_str = ""

        mapping = {
            "#event-title": self.name,
            "#event-message": (self.message or "").strip(),
            "#event-date": date_str,
            "#event-time": time_str,
            "#event-location": (getattr(self, "location", "") or "").strip(),
        }
        for sel, val in mapping.items():
            el = soup.select_one(sel) or _ensure_el(sel, "span")
            _set_text(el, val)

        # Slug / link
        link = (self.secure_invite_link or "").strip() if prefer_secure_link else ""
        if not link:
            # fallback: site içi görünüm
            link = f"/invitations/{self.slug}/"

        slug_el = soup.select_one("#inv-slug")
        if slug_el:
            _set_text(slug_el, self.slug)

        rsvp_link = soup.select_one("#rsvp-link")
        if rsvp_link:
            _set_attr(rsvp_link, "href", link)

        # 3) E-postalar için script’leri ve contenteditable’ları temizle
        for tag in soup.find_all(attrs={"contenteditable": True}):
            try:
                del tag["contenteditable"]
            except Exception:
                pass

        if strip_scripts:
            for s in soup.find_all("script"):
                s.decompose()

        return str(soup)
    # ---- NEW: Backend validation (kredi yoksa reminders açılamaz)
    def clean(self):
        super().clean()
        if self.reminders:
            user = getattr(self.project, "owner", None)
            if not user:
                raise ValidationError({"project": "Sahip bilgisi eksik."})
            if get_reminder_credits(user) < 1:
                raise ValidationError({"reminders": "Hatırlatma hakkınız yok. Planınızı yükseltin."})

    def save(self, *args, **kwargs):
        """Custom save method to auto-fill fields and schedule reminders."""
        if not self.invitation_date:
            self.invitation_date = timezone.now()

        if not self.slug:
            base_slug = slugify(self.name)
            unique_suffix = str(uuid.uuid4())[:8]
            self.slug = f"{base_slug}-{unique_suffix}"

        if self.is_password_protected and not self.password:
            self.password = get_random_string(length=16)

        self.secure_invite_link = generate_secure_invitation_link(self)

        # Önce kaydet (id gerekiyor)
        super().save(*args, **kwargs)

        # Planlama: reminders=True, automation=False ve gönderilebilir ise
        if self.reminders and not self.automation and self.can_send:
            self.schedule_reminders()

    def schedule_reminders(self):
        """Kalan krediye göre gelecekteki slotları planla ve krediyi tüket."""
        if not self.can_send:
            return

        now = timezone.now()
        times = self.reminder_config or [1440, 60, 30]  # dakika
        # Geleceğe düşen slotları topla
        future_slots = []
        for minutes_before in times:
            send_time = self.invitation_date - timedelta(minutes=minutes_before)
            if send_time > now:
                future_slots.append(send_time)

        if not future_slots:
            return

        # max_reminders sınırı + daha önce gönderilenler
        remain_allowed = max(self.max_reminders - self.reminders_sent, 0)
        future_slots = future_slots[:remain_allowed]
        if not future_slots:
            return

        # Alıcılar
        recipient_emails = list(self.recipients.values_list('email', flat=True))
        if not recipient_emails:
            # alıcı yoksa kredi tüketme / job kurma
            return

        # Kullanıcı & kredi tüketimi (1 slot = 1 kredi)
        user = getattr(self.project, "owner", None)
        if not user:
            raise ValidationError("Sahip bilgisi eksik.")

        needed_credits = len(future_slots)
        consume_reminder_credits(user, needed_credits)

        # E-postaları planla
        for send_time in future_slots:
            scheduler.schedule_email(
                recipients=recipient_emails,
                send_time=send_time,
                subject=f"Reminder: {self.name}",
                message=self.reminder_message or self.message,
                callback=self.update_last_reminder_sent,
            )
            self.reminders_sent += 1

        # Otomasyon artık kuruldu
        self.automation = True
        self.save(update_fields=['reminders_sent', 'automation'])

    def update_last_reminder_sent(self, *args, **kwargs):
        self.last_reminder_sent = timezone.now()
        self.save(update_fields=['last_reminder_sent'])

    def is_expired(self):
        """Check if the invitation has expired."""
        return self.invitation_date < timezone.now()

    class Meta:
        verbose_name = "Invitation"
        verbose_name_plural = "Invitations"
        ordering = ['name']
