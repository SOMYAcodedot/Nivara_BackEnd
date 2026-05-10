from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nivara_app', '0007_chat_sessions'),
    ]

    operations = [
        migrations.AddField(
            model_name='moodentry',
            name='question_responses',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='moodentry',
            name='is_assessment_based',
            field=models.BooleanField(default=False),
        ),
    ]
