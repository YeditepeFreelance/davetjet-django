from django.utils import timezone
from .views import send_scheduled_email
from celery import shared_task
from django.core.mail import send_mail

# Celery task to send email
@shared_task
def send_scheduled_email(subject, message, recipient_list, from_email=None):
  send_mail(
    subject,
    message,
    from_email,
    recipient_list,
    fail_silently=False,
  )

# Function to schedule the email task
def schedule_email(subject, message, recipient_list, send_time, from_email=None):
    """
    datetime.
    send_time: timezone-aware datetime object
    """
    # Calculate the delay in seconds

    delay = (send_time - timezone.now()).total_seconds()
    if delay < 0:
        delay = 0  # If send_time is in the past, send immediately

    send_scheduled_email.apply_async(
        args=[subject, message, recipient_list, from_email],
        countdown=delay
    )