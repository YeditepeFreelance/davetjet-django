from django.apps import AppConfig

class InvitationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'invitations'

    def ready(self):
        import invitations.signals  # 👈 Signal dosyasını burada import et
