from rest_framework import serializers
from .models import Invitation
from projects.models import Project


# — LİSTE/ÖZET (dokunmuyoruz) —
class InvitationSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = ['id', 'name', 'type', 'url']

    def get_type(self, obj):
        return 'invitation'

    def get_url(self, obj):
        return f"/invitations/{obj.id}/"


# — DETAY (GET/PATCH için TAM alanlar) —
class InvitationDetailSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    # JSON alanları explicit tanımlayalım ki yutulmasın
    reminder_config = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False, allow_null=True, default=list
    )
    delivery_settings = serializers.JSONField(required=False, default=dict)
    reminder_message = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    reminders = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Invitation
        fields = (
            "id", "type", "url",
            "created_at", "updated_at",
            "is_draft", "published_at",

            "name", "slug", "project",
            "message", "invitation_date", "location",

            "template",

            "is_password_protected", "password", "secure_invite_link",

            "reminders", "reminder_message", "reminder_config",
            "max_reminders", "reminders_sent", "last_reminder_sent",

            "channels", "delivery_settings",

            "automation", "retry_count", "max_retries",
        )
        read_only_fields = ("slug", "secure_invite_link", "created_at", "updated_at", "published_at")

    def get_type(self, obj): return "invitation"
    def get_url(self, obj):  return f"/invitations/{obj.id}/"

    def validate(self, attrs):
        # Taslakta serbest; publish'te (is_draft=False) sıkı kontrol
        is_draft = attrs.get("is_draft", getattr(self.instance, "is_draft", True))
        reminders = attrs.get("reminders", getattr(self.instance, "reminders", False))
        if not is_draft and reminders:
            cfg = attrs.get("reminder_config", getattr(self.instance, "reminder_config", [])) or []
            ds  = attrs.get("delivery_settings", getattr(self.instance, "delivery_settings", {})) or {}
            if not cfg:
                raise serializers.ValidationError({"reminder_config": "En az bir hatırlatma zamanı seçin."})
            if not (ds.get("email") or ds.get("sms") or ds.get("whatsapp")):
                raise serializers.ValidationError({"delivery_settings": "En az bir hatırlatma kanalı seçin."})
        return attrs

    def update(self, instance, validated_data):
        if validated_data.get("reminders") is False:
            validated_data.setdefault("reminder_config", [])
            validated_data.setdefault("reminder_message", "")
        return super().update(instance, validated_data)


# — CREATE (POST; Project oluşturma mantığın korunuyor) —

# invitations/serializers.py

class CreateInvitationSerializer(serializers.ModelSerializer):
    # ekstra alanlar
    is_draft = serializers.BooleanField(required=False, default=True)

    reminder_config = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False, allow_null=True, default=list
    )
    delivery_settings = serializers.JSONField(required=False, default=dict)
    reminder_message = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="")
    reminders = serializers.BooleanField(required=False, default=False)

    is_password_protected = serializers.BooleanField(required=False, default=False)
    password = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Invitation
        fields = [
            # temel
            'name', 'message', 'invitation_date', 'location', 'template',
            # draft/publish
            'is_draft',
            # güvenlik
            'is_password_protected', 'password',
            # hatırlatıcılar
            'reminders', 'reminder_message', 'reminder_config',
            # teslimat
            'channels', 'delivery_settings',
        ]

    def validate(self, attrs):
        is_draft = attrs.get("is_draft", True)
        reminders = attrs.get("reminders", False)
        if not is_draft and reminders:
            cfg = attrs.get("reminder_config") or []
            ds  = attrs.get("delivery_settings") or {}
            if not cfg:
                raise serializers.ValidationError({"reminder_config": "En az bir hatırlatma zamanı seçin."})
            if not (ds.get("email") or ds.get("sms") or ds.get("whatsapp")):
                raise serializers.ValidationError({"delivery_settings": "En az bir hatırlatma kanalı seçin."})
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        if not user.is_authenticated:
            raise serializers.ValidationError("User must be authenticated to create an invitation.")
        project = Project.objects.create(
            owner=user,
            name=f'{user.username}-{validated_data.get("name")}-{str(validated_data.get("invitation_date"))}'
        )
        validated_data['project'] = project
        validated_data.pop('user', None)
        invitation = Invitation.objects.create(**validated_data)
        invitation.save()
        return invitation
