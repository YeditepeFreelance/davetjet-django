# invitations/serializers.py

from rest_framework import serializers
from .models import Invitation

class InvitationSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = ['id', 'name', 'type', 'url']

    def get_type(self, obj):
        return 'invitation'

    def get_url(self, obj):
        # Customize URL to where this invitation can be viewed in your app
        return f"/invitations/{obj.id}/"
