from rest_framework import serializers
from don_home.models import Ably_token, Cafe24

class AblySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ably_token
        fields = '__all__'

class Cafe24Serializer(serializers.ModelSerializer):
    class Meta:
        model = Cafe24
        fields = '__all__'