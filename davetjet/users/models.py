from datetime import timedelta
import sys
from math import ceil
from django.db import models
from django.apps import apps
from django.contrib.auth.models import AbstractUser, Group, Permission

from davetjet.config import language_choices
from django.db.models import Max, Q, Count
from django.utils import timezone

from invitations.models import Invitation
from projects.models import Project
from recipients.models import Recipient

class User(AbstractUser):
    """
    Custom user model that extends the default Django user model.
    """

    # Contact information
    email = models.EmailField(unique=True)

    phone_number = models.CharField(max_length=15, blank=True, null=True)
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Security features

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(auto_now=True)
    active_devices = models.JSONField(default=list, blank=True)
    reminder_credits = models.IntegerField(default=3)
    recipient_quota_limit = models.PositiveIntegerField(default=200)


    # Related models

    profile = models.OneToOneField('Profile', on_delete=models.CASCADE, related_name='user_profile', blank=True, null=True)
    subscriptions = models.ManyToManyField('payments.Subscription', related_name='subscribed_users', blank=True)

    # Permissions
    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

    def __str__(self):
        return self.username 

    
    def get_statistics(self, range_hours=24):
        projects = Project.objects.filter(owner=self)
        if not projects.exists():
            return None, {
                "invitee_count": 0,
                "recipient_count_change": 0,
                "recipient_count_change_pct": 0.0,
                "rsvp_ratio": 0.0,
                "rsvp_ratio_change": 0.0,
                "last_reminder_sent": None,
                "time_left": None,
                "event_date": None,
                "status_counts": {"yes": 0, "maybe": 0, "no": 0, "pending": 0},
            }

        projects.first().save()
        project_ids = list(projects.values_list("id", flat=True))
        # --- Tüm davetliler (tekrarsız) ---
        recs = (
            Recipient.objects
            .filter(invitations__project_id__in=project_ids)  # OneToOne / FK fark etmez, Invitation üstünde project_id var
            .distinct()
        )
        invitee_count = recs.count()

        email_reachable = recs.filter(email__isnull=False).count()
        sms_reachable = recs.filter(phone_number__isnull=False).count()

        # --- Anlık durum dağılımı ---
        status_rows = recs.values("rsvp_status").annotate(c=Count("id"))
        counts = {r["rsvp_status"]: r["c"] for r in status_rows}
        yes = counts.get("yes", 0)
        maybe = counts.get("maybe", 0)
        no = counts.get("no", 0)
        pending = counts.get("pending", 0)

        responded = yes + maybe + no
        rsvp_ratio = (responded / invitee_count) if invitee_count else 0.0  # 0–1

        # --- Değişimler: periyot başlangıcına göre ---
        start_dt = timezone.now() - timedelta(hours=range_hours)

        # Periyot BAŞINDA mevcut olan davetliler
        past_recs = recs.filter(created_at__lte=start_dt)
        prev_total = past_recs.count()

        # Kişi sayısı değişimi (mutlak & yüzde)
        recipient_count_change = invitee_count - prev_total
        if prev_total:
            recipient_count_change_pct = (recipient_count_change / prev_total) * 100.0
        else:
            recipient_count_change_pct = 100.0 if invitee_count > 0 else 0.0

        # Periyot başında yanıtlayanlar (yaklaşık)
        previously_responded = (
            past_recs.filter(updated_at__lte=start_dt)
                    .exclude(rsvp_status="pending")
                    .count()
        )
        prev_ratio = (previously_responded / prev_total) if prev_total else 0.0  # 0–1
        rsvp_ratio_change = (rsvp_ratio - prev_ratio) * 100.0  # yüzde puan

        # --- En yakın etkinlik / davetiye ---
        closest_invitation = (
            Invitation.objects
            .filter(project_id__in=project_ids, is_draft=False)
            .order_by("invitation_date")
            .first()
        )
        event_date = closest_invitation.invitation_date if closest_invitation else None

        # === time_left (saat/gün/ay) ===
        time_left = None
        if event_date:
            now = timezone.now()
            delta = event_date - now
            secs = delta.total_seconds()
            if secs <= 0:
                time_left = "Yok"
            else:
                hours = ceil(secs / 3600)
                days = ceil(secs / 86400)
                if days < 1:
                    value, unit = hours, "saat"
                elif days > 30:
                    months = ceil(days / 30)
                    value, unit = months, "ay"
                else:
                    value, unit = days, "gün"
                time_left = f"{int(value)} {unit}"

        # --- yüzde formatına çevir (tam sayı istiyorsan int(round())) ---
        rsvp_ratio_pct = int(round(rsvp_ratio * 100.0, 0))
        rsvp_ratio_change_pct = int(round(rsvp_ratio_change, 0))
        recipient_count_change_pct = int(round(recipient_count_change_pct, 0))

        # --- Son hatırlatma ---
        last_reminder_sent = (
            Invitation.objects
            .filter(project_id__in=project_ids, last_reminder_sent__isnull=False)
            .order_by("-last_reminder_sent")
            .values_list("last_reminder_sent", flat=True)
            .first()
        )

        return closest_invitation, {
            "invitee_count": invitee_count,
            "recipient_count_change": recipient_count_change,
            "recipient_count_change_pct": recipient_count_change_pct,  # %
            "rsvp_ratio": rsvp_ratio_pct,                              # %
            "rsvp_ratio_change": rsvp_ratio_change_pct,                # yüzde puan
            "last_reminder_sent": last_reminder_sent or "Yok",
            "time_left": time_left,
            "event_date": event_date,
            "status_counts": {"yes": yes, "maybe": maybe, "no": no, "pending": pending},
            "email_reachable": email_reachable,
            "sms_reachable": sms_reachable,
        }
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['username']

class Profile(models.Model):
    """
    User profile model that extends the User model.
    """
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile_obj')
    
    full_name = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    language = models.CharField(max_length=10, default='en', choices=language_choices or list)
    location = models.CharField(max_length=255, blank=True, null=True)
    social_links = models.JSONField(default=dict, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'
        ordering = ['user__username']
