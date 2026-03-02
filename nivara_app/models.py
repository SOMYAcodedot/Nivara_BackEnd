from django.db import models
from django.contrib.auth.models import AbstractUser

# Added Comments for clarity and alignment with views.py and AI Engine logic

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
# =========================================================

class MoodEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mood_entries")

    mood_text = models.TextField()
    mood_rating = models.IntegerField(null=True, blank=True)  # 1-5 scale

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "mood_entries"

    def __str__(self):
        return f"{self.user.username} - {self.mood_rating}"


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