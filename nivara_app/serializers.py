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


# ✅ Mood Entry Serializer (Phase 2 Enhanced)
class MoodEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodEntry
        fields = ['id', 'mood_score', 'emotion_type', 'journal_text', 'entry_date', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_mood_score(self, value):
        if value < 1 or value > 10:
            raise serializers.ValidationError("Mood score must be between 1 and 10")
        return value


# ✅ Mood Entry List Serializer (For history view with all fields)
class MoodEntryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodEntry
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at']


# ✅ Cycle Entry Serializer
class CycleEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CycleEntry
        fields = '__all__'