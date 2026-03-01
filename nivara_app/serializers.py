from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import MoodEntry, CycleEntry

User = get_user_model()


# ✅ Signup Serializer
class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


# ✅ Mood Entry Serializer
class MoodEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodEntry
        fields = '__all__'


# ✅ Cycle Entry Serializer
class CycleEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CycleEntry
        fields = '__all__'