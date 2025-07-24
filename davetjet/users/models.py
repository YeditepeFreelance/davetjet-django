from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

from davetjet.config import language_choices

class User(AbstractUser):
    """
    Custom user model that extends the default Django user model.
    """

    # Contact information

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
