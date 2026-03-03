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