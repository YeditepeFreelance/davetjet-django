from rest_framework import serializers
from .models import Recipient

class RecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipient
        fields = '__all__'
class RecipientNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipient
        fields = ['id', 'name']

class RSVPUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipient
        fields = ['name', 'rsvp_status']
