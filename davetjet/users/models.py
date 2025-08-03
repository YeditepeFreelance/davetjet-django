import sys
from django.db import models
from django.apps import apps
from django.contrib.auth.models import AbstractUser, Group, Permission

from davetjet.config import language_choices
from django.db.models import Max
from django.utils import timezone

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

    def get_statistics(self):
        projects = self.projects.all()
        if not projects:
            return {
                'invitee_count': 0,
                'rsvp_ratio': 0,
                'last_reminder_sent': None,
                'event_date': None
            }

        project_ids = projects.values_list('id', flat=True)
        invitee_count = sum(project.recipients.count() for project in projects)

        rsvp_ratio = 1 # Placeholder for RSVP ratio calculation
        # Get all invitations related to the user's projects as a queryset
        Invitation = apps.get_model('invitations', 'Invitation')  # Replace 'your_app_name' with the actual app name
        invitations_qs = Invitation.objects.filter(project_id__in=project_ids)
        last_reminder_sent = invitations_qs.aggregate(latest_reminder=Max('last_reminder_sent'))['latest_reminder']
        event_date = invitations_qs.aggregate(latest_event=Max('invitation_date'))['latest_event']

        # Calculate time left to the event (in days and hours) using basic functions
        time_left = None
        if event_date:
            now = timezone.now()
            delta = event_date - now
            print(f"Time left for event: {delta}", file=sys.stderr)
            if delta.total_seconds() > 0:
                days_left = delta.days
                hours_left = delta.seconds // 3600
                time_left = {'days': days_left, 'hours': hours_left}
            else:
                time_left = {'days': 0, 'hours': 0}

        return {
            'invitee_count': invitee_count if invitee_count else 0,
            'rsvp_ratio': f'%{rsvp_ratio * 100}' if rsvp_ratio else 0,
            'last_reminder_sent': last_reminder_sent if last_reminder_sent else "Yok",
            'event_date': event_date if event_date else None,
            'time_left': f"{time_left['days']} Gün" if time_left['days'] > 0 else f"{time_left['hours']} Saat" if time_left['hours'] > 0 else "Geldi!"
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
