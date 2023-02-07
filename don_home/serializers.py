from rest_framework import serializers
from don_home.models import Ably_token, Cafe24, AblyProductInfo, AblySalesInfo

class AblySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ably_token
        fields = '__all__'

class Cafe24Serializer(serializers.ModelSerializer):
    class Meta:
        model = Cafe24
        fields = '__all__'

class AblyProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AblyProductInfo
        fields = '__all__'

class AblySalseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AblySalesInfo
        fields = '__all__'