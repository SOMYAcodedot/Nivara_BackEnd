from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import MoodEntry, CycleEntry, CycleProfile, PeriodLog, DailyCheckin

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


# ✅ Cycle Entry Serializer (Legacy)
class CycleEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CycleEntry
        fields = '__all__'


# =========================================================
# 🌸 PHASE 3: CYCLE INTELLIGENCE SERIALIZERS
# =========================================================

# ✅ Cycle Profile Serializer (Onboarding)
class CycleProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating cycle profile during onboarding.
    """
    class Meta:
        model = CycleProfile
        fields = [
            'id',
            'last_period_start_date',
            'average_cycle_length',
            'average_cycle_length_days',
            'average_period_length',
            'average_period_length_days',
            'cycle_regularity',
            'flow_intensity_last_period',
            'spotting_between_periods',
            'typical_pms_symptoms',
            'birth_control_status',
            'reproductive_status',
            'is_onboarding_complete',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 
            'average_cycle_length_days', 
            'average_period_length_days',
            'created_at', 
            'updated_at'
        ]
    
    def validate_typical_pms_symptoms(self, value):
        """Validate PMS symptoms is a list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("PMS symptoms must be a list")
        
        valid_symptoms = [
            'mood_swings', 'irritability', 'anxiety', 'low_mood', 
            'bloating', 'breast_tenderness', 'headache', 'fatigue', 
            'cramps', 'acne', 'sleep_disturbance', 'no_symptoms', 'not_sure'
        ]
        for symptom in value:
            if symptom not in valid_symptoms:
                raise serializers.ValidationError(f"Invalid symptom: {symptom}")
        return value


class CycleProfileCreateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for cycle profile creation during onboarding.
    Allows simpler input without requiring all fields.
    """
    class Meta:
        model = CycleProfile
        fields = [
            'last_period_start_date',
            'average_cycle_length',
            'average_period_length',
            'cycle_regularity',
            'flow_intensity_last_period',
            'spotting_between_periods',
            'typical_pms_symptoms',
            'birth_control_status',
            'reproductive_status',
        ]
    
    def create(self, validated_data):
        validated_data['is_onboarding_complete'] = True
        return super().create(validated_data)


# ✅ Period Log Serializer
class PeriodLogSerializer(serializers.ModelSerializer):
    """
    Serializer for logging new periods.
    """
    class Meta:
        model = PeriodLog
        fields = [
            'id',
            'period_start_date',
            'period_end_date',
            'flow_intensity',
            'severe_pain',
            'notes',
            'actual_period_length',
            'cycle_length_from_previous',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 
            'actual_period_length', 
            'cycle_length_from_previous',
            'created_at', 
            'updated_at'
        ]


class PeriodLogCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating period log entries.
    """
    class Meta:
        model = PeriodLog
        fields = [
            'period_start_date',
            'period_end_date',
            'flow_intensity',
            'severe_pain',
            'notes'
        ]


class PeriodLogUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating period log (e.g., adding end date).
    """
    class Meta:
        model = PeriodLog
        fields = [
            'period_end_date',
            'flow_intensity',
            'severe_pain',
            'notes'
        ]


# ✅ Daily Checkin Serializer
class DailyCheckinSerializer(serializers.ModelSerializer):
    """
    Serializer for daily symptom and mood checkins.
    """
    class Meta:
        model = DailyCheckin
        fields = [
            'id',
            'checkin_date',
            'mood',
            'energy_level',
            'physical_symptoms',
            'user_notes',
            'cycle_day',
            'cycle_phase',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id', 
            'cycle_day', 
            'cycle_phase',
            'created_at', 
            'updated_at'
        ]
    
    def validate_mood(self, value):
        """Validate mood is a list of valid moods."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Mood must be a list")
        
        valid_moods = [
            'calm', 'happy', 'irritated', 'anxious', 
            'emotional', 'low', 'motivated', 'overwhelmed'
        ]
        for mood in value:
            if mood not in valid_moods:
                raise serializers.ValidationError(f"Invalid mood: {mood}")
        return value
    
    def validate_physical_symptoms(self, value):
        """Validate physical symptoms is a list of valid symptoms."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Physical symptoms must be a list")
        
        valid_symptoms = [
            'cramps', 'headache', 'bloating', 'breast_tenderness',
            'fatigue', 'acne', 'back_pain', 'nausea', 'no_symptoms'
        ]
        for symptom in value:
            if symptom not in valid_symptoms:
                raise serializers.ValidationError(f"Invalid symptom: {symptom}")
        return value


class DailyCheckinCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating daily checkins.
    """
    class Meta:
        model = DailyCheckin
        fields = [
            'checkin_date',
            'mood',
            'energy_level',
            'physical_symptoms',
            'user_notes'
        ]


# =========================================================
# 🎯 RESPONSE SERIALIZERS (For Dashboard Responses)
# =========================================================

class CycleStatusSerializer(serializers.Serializer):
    """
    Serializer for cycle status response (read-only).
    """
    cycle_day = serializers.IntegerField()
    cycle_phase = serializers.CharField()
    phase_display = serializers.CharField()
    days_until_next_period = serializers.IntegerField()
    pms_window = serializers.BooleanField()
    predicted_next_period = serializers.CharField()
    countdown_message = serializers.CharField()
    is_fertile_today = serializers.BooleanField()
    fertile_window = serializers.DictField()
    phase_description = serializers.CharField()
    energy_level = serializers.CharField()
    hormone_status = serializers.CharField()
    phase_tips = serializers.ListField(child=serializers.CharField())


class CycleDashboardSerializer(serializers.Serializer):
    """
    Comprehensive serializer for full cycle dashboard response.
    """
    cycle_profile = serializers.DictField()
    current_cycle_status = serializers.DictField()
    recent_checkin = serializers.DictField()
    personalized_insights = serializers.DictField()
    irregularity_analysis = serializers.DictField(allow_null=True)