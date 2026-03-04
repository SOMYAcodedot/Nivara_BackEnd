from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import date

# Added Comments for clarity and alignment with views.py and AI Engine logic
# added comment for check

# =========================================================
# 👤 CUSTOM USER MODEL
# =========================================================

class User(AbstractUser):
    age = models.IntegerField(null=True, blank=True)
    avg_cycle_length = models.IntegerField(default=28)
    is_female = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='nivara_users',
        blank=True,
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='nivara_user_permissions',
        blank=True,
    )

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.username


# =========================================================
# 🌸 MOOD ENTRY (Aligned with views.py + AI Engine)
# Phase 2: Enhanced Mood Logging & Emotional Intelligence
# =========================================================

class MoodEntry(models.Model):
    EMOTION_CHOICES = [
        ('happy', 'Happy'),
        ('calm', 'Calm'),
        ('anxious', 'Anxious'),
        ('sad', 'Sad'),
        ('irritated', 'Irritated'),
        ('stressed', 'Stressed'),
        ('excited', 'Excited'),
        ('tired', 'Tired'),
        ('neutral', 'Neutral'),
        ('hopeful', 'Hopeful'),
        ('overwhelmed', 'Overwhelmed'),
        ('content', 'Content'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mood_entries")

    mood_score = models.IntegerField(default=5)  # 1-10 scale
    emotion_type = models.CharField(max_length=20, choices=EMOTION_CHOICES, default='neutral')
    journal_text = models.TextField(blank=True, null=True)  # Optional journal entry
    entry_date = models.DateField(default=date.today)  # Date of mood entry

    # Legacy fields for backward compatibility
    mood_text = models.TextField(blank=True, null=True)
    mood_rating = models.IntegerField(null=True, blank=True)  # Legacy 1-5 scale

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-entry_date", "-created_at"]
        db_table = "mood_entries"

    def __str__(self):
        return f"{self.user.username} - {self.mood_score}/10 - {self.emotion_type}"


# =========================================================
# 🌙 CYCLE ENTRY (Aligned with predict_cycle logic)
# =========================================================

class CycleEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cycle_entries")

    last_period_date = models.DateField()
    average_cycle_length = models.IntegerField(default=28)

    symptoms = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "cycle_entries"

    def __str__(self):
        return f"{self.user.username} - {self.last_period_date}"


# =========================================================
# 🌸 PHASE 3: CYCLE INTELLIGENCE LAYER
# =========================================================

# =========================================================
# 🌼 CYCLE PROFILE (One-Time Onboarding)
# =========================================================

class CycleProfile(models.Model):
    """
    Stores user's initial cycle setup data - collected once during onboarding.
    """
    
    CYCLE_LENGTH_CHOICES = [
        ('21-24', '21-24 days'),
        ('25-28', '25-28 days'),
        ('29-32', '29-32 days'),
        ('33-35', '33-35 days'),
        ('35+', 'More than 35 days'),
        ('not_sure', 'Not sure'),
    ]
    
    PERIOD_LENGTH_CHOICES = [
        ('2-3', '2-3 days'),
        ('3-4', '3-4 days'),
        ('5-6', '5-6 days'),
        ('7+', '7+ days'),
        ('not_sure', 'Not sure'),
    ]
    
    REGULARITY_CHOICES = [
        ('mostly_regular', 'Yes, mostly regular'),
        ('sometimes_irregular', 'Sometimes irregular'),
        ('very_unpredictable', 'Very unpredictable'),
        ('not_sure', 'Not sure'),
    ]
    
    FLOW_INTENSITY_CHOICES = [
        ('light', 'Light'),
        ('moderate', 'Moderate'),
        ('heavy', 'Heavy'),
        ('very_heavy', 'Very heavy'),
        ('not_sure', 'Not sure'),
    ]
    
    SPOTTING_CHOICES = [
        ('never', 'Never'),
        ('occasionally', 'Occasionally'),
        ('frequently', 'Frequently'),
        ('not_sure', 'Not sure'),
    ]
    
    BIRTH_CONTROL_CHOICES = [
        ('no', 'No'),
        ('pill', 'Yes – Pill'),
        ('hormonal_iud', 'Yes – Hormonal IUD'),
        ('copper_iud', 'Yes – Copper IUD'),
        ('patch_ring', 'Yes – Patch / Ring'),
        ('prefer_not_say', 'Prefer not to say'),
    ]
    
    REPRODUCTIVE_STATUS_CHOICES = [
        ('none', 'None'),
        ('trying_to_conceive', 'Trying to conceive'),
        ('pregnant', 'Pregnant'),
        ('postpartum', 'Postpartum'),
        ('prefer_not_say', 'Prefer not to say'),
    ]
    
    PMS_SYMPTOM_CHOICES = [
        ('mood_swings', 'Mood swings'),
        ('irritability', 'Irritability'),
        ('anxiety', 'Anxiety'),
        ('low_mood', 'Low mood'),
        ('bloating', 'Bloating'),
        ('breast_tenderness', 'Breast tenderness'),
        ('headache', 'Headache'),
        ('fatigue', 'Fatigue'),
        ('cramps', 'Cramps'),
        ('acne', 'Acne'),
        ('sleep_disturbance', 'Sleep disturbance'),
        ('no_symptoms', 'No noticeable symptoms'),
        ('not_sure', 'Not sure'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cycle_profile")
    
    # Core cycle data
    last_period_start_date = models.DateField()
    average_cycle_length = models.CharField(max_length=20, choices=CYCLE_LENGTH_CHOICES, default='25-28')
    average_cycle_length_days = models.IntegerField(default=28)  # Computed numeric value
    average_period_length = models.CharField(max_length=20, choices=PERIOD_LENGTH_CHOICES, default='5-6')
    average_period_length_days = models.IntegerField(default=5)  # Computed numeric value
    
    # Cycle characteristics
    cycle_regularity = models.CharField(max_length=30, choices=REGULARITY_CHOICES, default='mostly_regular')
    flow_intensity_last_period = models.CharField(max_length=20, choices=FLOW_INTENSITY_CHOICES, default='moderate')
    spotting_between_periods = models.CharField(max_length=20, choices=SPOTTING_CHOICES, default='never')
    
    # PMS symptoms (stored as JSON list)
    typical_pms_symptoms = models.JSONField(default=list, blank=True)
    
    # Health status
    birth_control_status = models.CharField(max_length=30, choices=BIRTH_CONTROL_CHOICES, default='no')
    reproductive_status = models.CharField(max_length=30, choices=REPRODUCTIVE_STATUS_CHOICES, default='none')
    
    # Metadata
    is_onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "cycle_profiles"
        verbose_name = "Cycle Profile"
        verbose_name_plural = "Cycle Profiles"
    
    def __str__(self):
        return f"{self.user.username} - Cycle Profile"
    
    def save(self, *args, **kwargs):
        # Convert range choices to numeric days
        cycle_mapping = {
            '21-24': 22, '25-28': 28, '29-32': 30, 
            '33-35': 34, '35+': 38, 'not_sure': 28
        }
        period_mapping = {
            '2-3': 3, '3-4': 4, '5-6': 5, '7+': 7, 'not_sure': 5
        }
        self.average_cycle_length_days = cycle_mapping.get(self.average_cycle_length, 28)
        self.average_period_length_days = period_mapping.get(self.average_period_length, 5)
        super().save(*args, **kwargs)


# =========================================================
# 🌿 PERIOD LOG (Ongoing Period Logging)
# =========================================================

class PeriodLog(models.Model):
    """
    Records each period occurrence for tracking and prediction accuracy.
    """
    
    FLOW_INTENSITY_CHOICES = [
        ('light', 'Light'),
        ('moderate', 'Moderate'),
        ('heavy', 'Heavy'),
        ('very_heavy', 'Very heavy'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="period_logs")
    
    period_start_date = models.DateField()
    period_end_date = models.DateField(null=True, blank=True)
    flow_intensity = models.CharField(max_length=20, choices=FLOW_INTENSITY_CHOICES, default='moderate')
    severe_pain = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    
    # Computed fields (updated when end date is set)
    actual_period_length = models.IntegerField(null=True, blank=True)
    cycle_length_from_previous = models.IntegerField(null=True, blank=True)  # Days since last period
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "period_logs"
        ordering = ["-period_start_date"]
        verbose_name = "Period Log"
        verbose_name_plural = "Period Logs"
    
    def __str__(self):
        return f"{self.user.username} - Period: {self.period_start_date}"
    
    def save(self, *args, **kwargs):
        # Calculate period length if end date exists
        if self.period_end_date and self.period_start_date:
            self.actual_period_length = (self.period_end_date - self.period_start_date).days + 1
        
        # Calculate cycle length from previous period
        previous_period = PeriodLog.objects.filter(
            user=self.user,
            period_start_date__lt=self.period_start_date
        ).order_by('-period_start_date').first()
        
        if previous_period:
            self.cycle_length_from_previous = (self.period_start_date - previous_period.period_start_date).days
        
        super().save(*args, **kwargs)


# =========================================================
# 🌻 DAILY CHECKIN (Optional Daily Symptom Updates)
# =========================================================

class DailyCheckin(models.Model):
    """
    Optional daily symptom and mood tracking during cycle.
    """
    
    MOOD_CHOICES = [
        ('calm', 'Calm'),
        ('happy', 'Happy'),
        ('irritated', 'Irritated'),
        ('anxious', 'Anxious'),
        ('emotional', 'Emotional'),
        ('low', 'Low'),
        ('motivated', 'Motivated'),
        ('overwhelmed', 'Overwhelmed'),
    ]
    
    ENERGY_LEVEL_CHOICES = [
        ('very_low', 'Very low'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
    ]
    
    PHYSICAL_SYMPTOM_CHOICES = [
        ('cramps', 'Cramps'),
        ('headache', 'Headache'),
        ('bloating', 'Bloating'),
        ('breast_tenderness', 'Breast tenderness'),
        ('fatigue', 'Fatigue'),
        ('acne', 'Acne'),
        ('back_pain', 'Back pain'),
        ('nausea', 'Nausea'),
        ('no_symptoms', 'No symptoms'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_checkins")
    
    checkin_date = models.DateField(default=date.today)
    
    # Mood - stored as JSON list for multi-select
    mood = models.JSONField(default=list, blank=True)
    
    # Energy level
    energy_level = models.CharField(max_length=20, choices=ENERGY_LEVEL_CHOICES, default='moderate')
    
    # Physical symptoms - stored as JSON list for multi-select
    physical_symptoms = models.JSONField(default=list, blank=True)
    
    # Optional notes
    user_notes = models.TextField(blank=True, null=True)
    
    # Link to cycle phase at time of checkin
    cycle_day = models.IntegerField(null=True, blank=True)
    cycle_phase = models.CharField(max_length=30, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "daily_checkins"
        ordering = ["-checkin_date"]
        verbose_name = "Daily Checkin"
        verbose_name_plural = "Daily Checkins"
        unique_together = ['user', 'checkin_date']  # One checkin per day
    
    def __str__(self):
        return f"{self.user.username} - Checkin: {self.checkin_date}"