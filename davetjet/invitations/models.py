from django.db import models
from davetjet.config import channel_choices

class Invitation(models.Model):
    name = models.CharField(max_length=100, unique=True)

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='invitations',
        help_text='The project associated with this invitation.'
    )
    recipients = models.ManyToManyField(
        'recipients.Recipient',
        related_name='invitations',
        blank=True,
        help_text='Recipients who can accept this invitation.'
    )

    message = models.TextField(
        blank=True,
        help_text='Optional message to include with the invitation.'
    )

    invitation_date = models.DateTimeField(
        help_text='The date and time when the invitation was sent.'
    )

    reminders = models.BooleanField(
        default=False,
        help_text='Indicates whether reminders should be sent for this invitation.'
    )

    channels = models.CharField(
        max_length=10,
        choices=channel_choices,
        default='email',
        help_text='Select the channel for this invitation.'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='The date and time when the invitation was created.'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='The date and time when the invitation was last updated.'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Invitation"
        verbose_name_plural = "Invitations"
        ordering = ['name']