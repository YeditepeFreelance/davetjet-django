from django.apps import AppConfig


class RecipientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recipients'
    # recipients/apps.py
    def ready(self):
        import recipients.signals  # Gerekli
