import uuid
from datetime import datetime, timedelta
from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.db.models import JSONField

from communication.scheduler import SchedulerService
from davetjet.config import channel_choices
from .utils import generate_secure_invitation_link

scheduler = SchedulerService()

# --- CONSTANTS ---
TEMPLATE_CHOICES = [
    ('classic', 'Classic'),
    ('modern', 'Modern'),
    ('minimal', 'Minimal'),
]


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
        related_name='invitations',
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
    secure_invite_link = models.URLField(max_length=200, blank=True)

    # --- AUTOMATION ---
    automation = models.BooleanField(default=False, help_text="Automation enabled?")
    retry_count = models.PositiveIntegerField(default=0, help_text="Retry count for unanswered reminders.")
    max_retries = models.PositiveIntegerField(default=1, help_text="Max retries for unanswered reminders.")

    # --- META ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_draft = models.BooleanField(default=True, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)  # EK

    # İsteğe bağlı: sadece yayınlanmış olanlar için convenience manager
    class Published(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(is_draft=False)

    objects = models.Manager()
    published = Published()
    # --- METHODS ---
    def __str__(self):
        return self.name

    @property
    def can_send(self) -> bool:
        """Gönderim/schedule yapılabilir mi?"""
        return (not self.is_draft) and (self.invitation_date is not None) and (not self.is_expired())
    def save(self, *args, **kwargs):
        """Custom save method to auto-fill fields and schedule reminders."""
        # Set event date if missing
        if not self.invitation_date:
            self.invitation_date = timezone.now()

        # Generate slug
        if not self.slug:
            base_slug = slugify(self.name)
            unique_suffix = str(uuid.uuid4())[:8]
            self.slug = f"{base_slug}-{unique_suffix}"

        # Auto-generate password
        if self.is_password_protected and not self.password:
            self.password = get_random_string(length=16)

        # Generate secure invite link
        self.secure_invite_link = generate_secure_invitation_link(self)

        # Schedule reminders if enabled and automation is not already set
        if self.reminders and not self.automation and self.can_send:
            self.schedule_reminders()
            self.automation = True

        super().save(*args, **kwargs)

    def schedule_reminders(self):
        """Schedule reminders based on reminder_config and limits."""
        # Default reminder times if not set
        if not self.can_send:
            return
        times = self.reminder_config or [1440, 60, 30]  # minutes before event

        for minutes_before in times:
            if self.reminders_sent >= self.max_reminders:
                break

            send_time = self.invitation_date - timedelta(minutes=minutes_before)
            scheduler.schedule_email(
                recipients=self.recipients.values_list('email', flat=True),
                send_time=send_time,
                subject=f"Reminder: {self.name}",
                message=self.reminder_message or self.message,
                callback=self.update_last_reminder_sent,
            )
            self.reminders_sent += 1

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
