# Generated by Django 5.2.2 on 2025-06-07 21:21

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invitations', '0003_invitation_project'),
    ]

    operations = [
        migrations.AddField(
            model_name='invitation',
            name='channels',
            field=models.CharField(choices=[('sms', 'SMS'), ('whatsapp', 'WhatsApp'), ('email', 'E-mail')], default='email', help_text='Select the channel for this invitation.', max_length=10),
        ),
        migrations.AddField(
            model_name='invitation',
            name='invitation_date',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, help_text='The date and time when the invitation was sent.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invitation',
            name='reminders',
            field=models.BooleanField(default=False, help_text='Indicates whether reminders should be sent for this invitation.'),
        ),
    ]
