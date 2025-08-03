import sys
import requests
from typing import Callable, List
from datetime import datetime, timedelta
from django.core.mail import EmailMessage
from django.conf import settings
import resend


resend.api_key = 're_VcHdWgFN_78GPcaxJj9J2KyRCSeiK77is'
DEFAULT_FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@davetjet.com')

def send_email_via_resend(
    recipients: list,
    subject: str,
    message: str,
    from_email=None,
    html_message=None
):
    """
    Sends individual emails using Resend API to simulate BCC behavior (privacy).
    Supports plain text and optional HTML content.
    """
    from_email = from_email or DEFAULT_FROM_EMAIL
    try:
        res = resend.Emails.send({
  "from": "Acme <onboarding@resend.dev>",
  "to": ["furkanesen1900@gmail.com"],
  "subject": "Hello from Resend Python SDK",
  "html": "<strong>This is a test email</strong>"
})
    except Exception as e   :
        print(str(e), file=sys.stderr)

def send_email(recipients: list, subject: str, message: str, from_email=None, html_message=None):
    """
    Send a bulk email to a list of recipients using BCC to keep addresses private.

    Args:
        recipients (list): List of email addresses to send the message to.
        subject (str): Subject of the email.
        message (str): Plain text version of the email.
        from_email (str, optional): The sender address. Defaults to settings.DEFAULT_FROM_EMAIL.
        html_message (str, optional): Optional HTML content.
    """
    from_email = from_email or settings.DEFAULT_FROM_EMAIL

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=from_email,
        to=[],  # Empty or one recipient
        bcc=recipients  # Use BCC to hide emails from each other
    )

    if html_message:
        email.content_subtype = "html"
        email.body = html_message

    email.send(fail_silently=False)

def send_whatsapp(recipient: str, message: str):
    """
    Placeholder function for sending WhatsApp messages.
    This should be implemented with an actual WhatsApp API integration.
    """
    
    response = requests.post('https://graph.facebook.com/v22.0/684626378062799/messages',json={
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "+905465952986",
  "type": "text",
  "text": {
    "preview_url": True,
    "body": "As requested, here's the link to our latest product: https://www.meta.com/quest/quest-3/"
  }
})

    if response.status_code != 200:
        raise Exception(f"Failed to send WhatsApp message: {response.text}")

    print(f"WhatsApp message sent to {recipient}: {message}", file=sys.stderr)