import sys
from django.db import models
from communication.scheduler import SchedulerService
from davetjet.config import channel_choices
from datetime import timedelta, datetime

scheduler = SchedulerService()
# scheduler.schedule_email(recipients=['furkanesen1900@gmail.com', 'furkanesenprivate@gmail.com'], send_time=datetime.now() + timedelta(seconds=10), subject="Test Email", message="This is a test email from the scheduler.")

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

    last_reminder_sent = models.DateTimeField(
        null=True,
        blank=True,
        help_text='The date and time when the last reminder was sent.'
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

    automation = models.BooleanField(
        default=False,
        help_text='Indicates whether this automation is started or not.'
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.invitation_date:
            from django.utils import timezone
            self.invitation_date = timezone.now()

        if not self.automation:
            self.automation = True  # Default to True if not set

            if not self.reminders:
                return super().save(*args, **kwargs)
            # Schedule the reminder if reminders are enabled
            reminders = [
                self.invitation_date - timedelta(days=1),
                self.invitation_date - timedelta(hours=1),
                self.invitation_date - timedelta(minutes=30),
                datetime.now() + timedelta(seconds=10)  # Immediate reminder for testing
            ]

            for reminder in reminders:
                scheduler.schedule_email(
                    self.recipients.values_list('email', flat=True),
                    reminder,
                    subject=f"Reminder: {self.name}",
                    message=self.message,
                    callback=self.update_last_reminder_sent,
                )
            # print(f"Scheduled reminders for {self.name} at {reminders}", file=sys.stderr)
        # Save the invitation

        super().save(*args, **kwargs)
    
    def update_last_reminder_sent(self):
        self.last_reminder_sent = datetime.now()
        self.save(update_fields=['last_reminder_sent'])

    class Meta:
        verbose_name = "Invitation"
        verbose_name_plural = "Invitations"
        ordering = ['name']