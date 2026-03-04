from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Count, StdDev
from django.db.models.functions import TruncDate, TruncWeek
from collections import Counter
import json
import re
from datetime import datetime, timedelta, date

from .models import MoodEntry, CycleEntry, CycleProfile, PeriodLog, DailyCheckin
from .serializers import (
    MoodEntrySerializer, 
    MoodEntryDetailSerializer, 
    CycleEntrySerializer,
    CycleProfileSerializer,
    CycleProfileCreateSerializer,
    PeriodLogSerializer,
    PeriodLogCreateSerializer,
    PeriodLogUpdateSerializer,
    DailyCheckinSerializer,
    DailyCheckinCreateSerializer
)

User = get_user_model()

# AI ENGINE IMPORTS
from .ai_engine.mood_analysis import analyze_mood_entries
from .ai_engine.chatbot_engine import chatbot_response
from .ai_engine.cycle_logic import (
    predict_cycle, 
    get_cycle_status, 
    get_full_cycle_dashboard,
    calculate_cycle_day,
    get_cycle_phase,
    detect_irregularity,
    generate_personalized_insights
)
from .ai_engine.lifestyle_ai import generate_lifestyle_plan
from .ai_engine.report_generator import generate_health_report


# =========================================================
# 🔐 AUTHENTICATION
# =========================================================

class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        username = request.data.get("username")
        password = request.data.get("password")

        if not email or not username or not password:
            return Response({"error": "All fields required"}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already registered"}, status=400)
        
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already taken"}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "User created successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            username = request.data.get("username")
            password = request.data.get("password")

            if not username or not password:
                return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            authenticated_user = authenticate(username=username, password=password)

            if authenticated_user:
                refresh = RefreshToken.for_user(authenticated_user)
                return Response({
                    "message": "Login successful",
                    "user": {
                        "id": authenticated_user.id,
                        "username": authenticated_user.username,
                        "email": authenticated_user.email
                    },
                    "access": str(refresh.access_token),
                    "refresh": str(refresh)
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(f"Login Error: {str(e)}")
            return Response({"error": f"Server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({"message": "Logged out successfully"}, status=200)
        except Exception as e:
            # If blacklist is not enabled, still return success
            # Client should remove tokens from localStorage
            return Response({"message": "Logged out successfully"}, status=200)


# =========================================================
# 🌸 MOOD LOGGING
# =========================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def log_mood(request):
    serializer = MoodEntrySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mood_history(request):
    moods = MoodEntry.objects.filter(user=request.user).order_by("-created_at")
    serializer = MoodEntrySerializer(moods, many=True)
    return Response(serializer.data)


# =========================================================
# 🧠 MOOD ANALYSIS
# =========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def run_mood_analysis(request):
    moods = MoodEntry.objects.filter(user=request.user)
    analysis = analyze_mood_entries(moods)
    return Response(analysis)


# =========================================================
# 📊 PHASE 2: MOOD ANALYTICS & GRAPHICAL DATA APIs
# =========================================================

# Stress keywords for analysis
STRESS_KEYWORDS = [
    'stressed', 'stress', 'anxious', 'anxiety', 'worried', 'worry',
    'overwhelmed', 'panic', 'nervous', 'tension', 'pressure', 'exhausted',
    'tired', 'burnout', 'frustrated', 'frustrated', 'irritated', 'angry',
    'sad', 'depressed', 'hopeless', 'lonely', 'scared', 'fear'
]


def calculate_stress_from_journal(journal_text):
    """Calculate stress score based on journal text keywords"""
    if not journal_text:
        return 0
    
    text_lower = journal_text.lower()
    count = sum(1 for keyword in STRESS_KEYWORDS if keyword in text_lower)
    return min(count, 10)  # Cap at 10


def get_emotion_category(emotion_type):
    """Categorize emotions into positive, negative, neutral"""
    positive = ['happy', 'calm', 'excited', 'hopeful', 'content']
    negative = ['anxious', 'sad', 'irritated', 'stressed', 'tired', 'overwhelmed']
    
    if emotion_type in positive:
        return 'positive'
    elif emotion_type in negative:
        return 'negative'
    return 'neutral'


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mood_trend_data(request):
    """
    API for Mood Trend Line Chart
    Returns mood scores over time for visualization
    Query params: days (default 30)
    """
    days = int(request.query_params.get('days', 30))
    start_date = datetime.now().date() - timedelta(days=days)
    
    moods = MoodEntry.objects.filter(
        user=request.user,
        entry_date__gte=start_date
    ).order_by('entry_date')
    
    # Group by date and get daily average
    daily_data = moods.values('entry_date').annotate(
        avg_mood=Avg('mood_score'),
        entries_count=Count('id')
    ).order_by('entry_date')
    
    trend_data = [
        {
            "date": entry['entry_date'].strftime('%Y-%m-%d'),
            "mood_score": round(entry['avg_mood'], 1) if entry['avg_mood'] else 0,
            "entries": entry['entries_count']
        }
        for entry in daily_data
    ]
    
    return Response({
        "period_days": days,
        "data_points": len(trend_data),
        "trend_data": trend_data
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def emotion_distribution(request):
    """
    API for Emotion Distribution Pie Chart
    Returns emotion type percentages
    Query params: days (default 30)
    """
    days = int(request.query_params.get('days', 30))
    start_date = datetime.now().date() - timedelta(days=days)
    
    moods = MoodEntry.objects.filter(
        user=request.user,
        entry_date__gte=start_date
    )
    
    total_entries = moods.count()
    if total_entries == 0:
        return Response({
            "period_days": days,
            "total_entries": 0,
            "distribution": [],
            "category_breakdown": {"positive": 0, "negative": 0, "neutral": 0}
        })
    
    # Count emotions
    emotion_counts = moods.values('emotion_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    distribution = [
        {
            "emotion": entry['emotion_type'],
            "count": entry['count'],
            "percentage": round((entry['count'] / total_entries) * 100, 1)
        }
        for entry in emotion_counts
    ]
    
    # Category breakdown
    category_counts = {"positive": 0, "negative": 0, "neutral": 0}
    for entry in emotion_counts:
        category = get_emotion_category(entry['emotion_type'])
        category_counts[category] += entry['count']
    
    category_breakdown = {
        k: round((v / total_entries) * 100, 1) 
        for k, v in category_counts.items()
    }
    
    return Response({
        "period_days": days,
        "total_entries": total_entries,
        "distribution": distribution,
        "category_breakdown": category_breakdown
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stress_pattern_data(request):
    """
    API for Stress Pattern Bar Graph
    Returns stress marker frequency analysis
    Query params: days (default 30)
    """
    days = int(request.query_params.get('days', 30))
    start_date = datetime.now().date() - timedelta(days=days)
    
    moods = MoodEntry.objects.filter(
        user=request.user,
        entry_date__gte=start_date
    )
    
    # Analyze stress from emotions and journal
    stress_emotions = ['anxious', 'stressed', 'irritated', 'overwhelmed', 'tired', 'sad']
    
    # Weekly stress analysis
    weekly_data = moods.annotate(
        week=TruncWeek('entry_date')
    ).values('week').annotate(
        total_entries=Count('id'),
        avg_mood=Avg('mood_score')
    ).order_by('week')
    
    # Count stress-related emotions per week
    stress_by_week = []
    for week_entry in weekly_data:
        week_start = week_entry['week']
        week_end = week_start + timedelta(days=7)
        
        week_moods = moods.filter(
            entry_date__gte=week_start,
            entry_date__lt=week_end
        )
        
        stress_emotion_count = week_moods.filter(
            emotion_type__in=stress_emotions
        ).count()
        
        # Calculate journal stress scores
        journal_stress = 0
        for mood in week_moods:
            if mood.journal_text:
                journal_stress += calculate_stress_from_journal(mood.journal_text)
        
        total = week_entry['total_entries']
        stress_percentage = round((stress_emotion_count / total) * 100, 1) if total > 0 else 0
        
        stress_by_week.append({
            "week_start": week_start.strftime('%Y-%m-%d'),
            "total_entries": total,
            "stress_emotion_count": stress_emotion_count,
            "stress_percentage": stress_percentage,
            "journal_stress_score": journal_stress,
            "avg_mood": round(week_entry['avg_mood'], 1) if week_entry['avg_mood'] else 0
        })
    
    # Overall keyword frequency
    keyword_frequency = Counter()
    for mood in moods:
        if mood.journal_text:
            text_lower = mood.journal_text.lower()
            for keyword in STRESS_KEYWORDS:
                if keyword in text_lower:
                    keyword_frequency[keyword] += 1
    
    top_stress_keywords = [
        {"keyword": k, "count": v}
        for k, v in keyword_frequency.most_common(10)
    ]
    
    return Response({
        "period_days": days,
        "weekly_stress_data": stress_by_week,
        "top_stress_keywords": top_stress_keywords
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mood_analytics_summary(request):
    """
    Comprehensive Mood Analytics API
    Returns all aggregated data for Phase 2 dashboard
    Query params: days (default 30)
    """
    days = int(request.query_params.get('days', 30))
    start_date = datetime.now().date() - timedelta(days=days)
    
    moods = MoodEntry.objects.filter(
        user=request.user,
        entry_date__gte=start_date
    )
    
    total_entries = moods.count()
    
    if total_entries == 0:
        return Response({
            "period_days": days,
            "total_entries": 0,
            "average_mood": 0,
            "dominant_emotion": None,
            "stress_level": "Unknown",
            "weekly_variation": 0,
            "mood_stability_index": 0,
            "cycle_phase": None,
            "message": "No mood entries found for this period"
        })
    
    # Calculate average mood
    avg_mood = moods.aggregate(avg=Avg('mood_score'))['avg'] or 0
    avg_mood = round(avg_mood, 1)
    
    # Calculate mood standard deviation (variance indicator)
    mood_scores = list(moods.values_list('mood_score', flat=True))
    if len(mood_scores) > 1:
        mean = sum(mood_scores) / len(mood_scores)
        variance = sum((x - mean) ** 2 for x in mood_scores) / len(mood_scores)
        std_dev = variance ** 0.5
        weekly_variation = round(std_dev, 1)
    else:
        weekly_variation = 0
    
    # Mood stability index (0-100, higher is more stable)
    # Based on inverse of variation normalized to 0-100
    max_possible_std = 4.5  # Max std for 1-10 scale
    stability_index = round(max(0, 100 - (weekly_variation / max_possible_std * 100)), 1)
    
    # Dominant emotion
    emotion_counts = moods.values('emotion_type').annotate(
        count=Count('id')
    ).order_by('-count')
    dominant_emotion = emotion_counts[0]['emotion_type'] if emotion_counts else None
    
    # Stress level calculation
    stress_emotions = ['anxious', 'stressed', 'irritated', 'overwhelmed', 'tired', 'sad']
    stress_count = moods.filter(emotion_type__in=stress_emotions).count()
    stress_percentage = (stress_count / total_entries) * 100 if total_entries > 0 else 0
    
    # Calculate journal-based stress
    journal_stress_total = 0
    entries_with_journal = 0
    for mood in moods:
        if mood.journal_text:
            entries_with_journal += 1
            journal_stress_total += calculate_stress_from_journal(mood.journal_text)
    
    avg_journal_stress = journal_stress_total / entries_with_journal if entries_with_journal > 0 else 0
    
    # Combined stress level
    combined_stress = (stress_percentage * 0.6) + (avg_journal_stress * 4)  # Weight and scale
    if combined_stress < 20:
        stress_level = "Low"
    elif combined_stress < 40:
        stress_level = "Moderate"
    elif combined_stress < 60:
        stress_level = "High"
    else:
        stress_level = "Very High"
    
    # Get current cycle phase if available
    latest_cycle = CycleEntry.objects.filter(user=request.user).order_by('-created_at').first()
    cycle_phase = None
    if latest_cycle:
        try:
            days_since_period = (datetime.now().date() - latest_cycle.last_period_date).days
            cycle_day = days_since_period % latest_cycle.average_cycle_length
            
            if cycle_day <= 5:
                cycle_phase = "Menstrual"
            elif cycle_day <= 13:
                cycle_phase = "Follicular"
            elif cycle_day <= 16:
                cycle_phase = "Ovulation"
            else:
                cycle_phase = "Luteal"
        except:
            cycle_phase = None
    
    return Response({
        "period_days": days,
        "total_entries": total_entries,
        "average_mood": avg_mood,
        "dominant_emotion": dominant_emotion,
        "stress_level": stress_level,
        "stress_percentage": round(stress_percentage, 1),
        "weekly_variation": weekly_variation,
        "mood_stability_index": stability_index,
        "cycle_phase": cycle_phase,
        "emotional_variance": round(weekly_variation, 2)
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mood_history_detailed(request):
    """
    Get detailed mood history with pagination
    Query params: days (default 30), limit (default 50)
    """
    days = int(request.query_params.get('days', 30))
    limit = int(request.query_params.get('limit', 50))
    start_date = datetime.now().date() - timedelta(days=days)
    
    moods = MoodEntry.objects.filter(
        user=request.user,
        entry_date__gte=start_date
    ).order_by('-entry_date', '-created_at')[:limit]
    
    serializer = MoodEntryDetailSerializer(moods, many=True)
    return Response({
        "period_days": days,
        "count": len(serializer.data),
        "entries": serializer.data
    })


# =========================================================
# 🌙 CYCLE TRACKING
# =========================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def log_cycle(request):
    serializer = CycleEntrySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def predict_cycle_view(request):
    last_period = request.data.get("last_period_date")
    avg_cycle = int(request.data.get("average_cycle_length", 28))

    result = predict_cycle(last_period, avg_cycle)
    return Response(result)


# =========================================================
# 🧘 LIFESTYLE AI
# =========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def lifestyle_plan(request):
    moods = MoodEntry.objects.filter(user=request.user)
    analysis = analyze_mood_entries(moods)
    plan = generate_lifestyle_plan(analysis)
    return Response(plan)


# =========================================================
# 📊 HEALTH REPORT GENERATOR
# =========================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_report(request):
    moods = MoodEntry.objects.filter(user=request.user)
    analysis = analyze_mood_entries(moods)

    cycles = CycleEntry.objects.filter(user=request.user)

    report = generate_health_report(analysis, cycles)
    return Response({"report": report})


# =========================================================
# 🤖 AI CHATBOT
# =========================================================

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def chat_with_ai(request):
    user_message = request.data.get("message", "").strip()

    if not user_message:
        return Response({"error": "Message required"}, status=400)

    response = chatbot_response(user_message)
    return Response({"response": response})


# =========================================================
# 🏠 DASHBOARD (INFO ONLY)
# =========================================================

class DashboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "message": "Welcome to Nivara Women’s Health AI System"
        })

# =========================================================
# 🌸 PHASE 3: CYCLE INTELLIGENCE LAYER APIs
# =========================================================

# =========================================================
# 📋 CYCLE PROFILE (Onboarding)
# =========================================================

class CycleProfileView(APIView):
    """
    API for managing user's cycle profile (onboarding data).
    GET: Retrieve current profile
    POST: Create new profile (onboarding)
    PUT/PATCH: Update existing profile
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user's cycle profile."""
        try:
            profile = CycleProfile.objects.get(user=request.user)
            serializer = CycleProfileSerializer(profile)
            return Response({
                "has_profile": True,
                "is_onboarding_complete": profile.is_onboarding_complete,
                "profile": serializer.data
            })
        except CycleProfile.DoesNotExist:
            return Response({
                "has_profile": False,
                "is_onboarding_complete": False,
                "message": "No cycle profile found. Please complete onboarding."
            })
    
    def post(self, request):
        """Create cycle profile during onboarding."""
        # Check if profile already exists
        if CycleProfile.objects.filter(user=request.user).exists():
            return Response({
                "error": "Profile already exists. Use PUT to update."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = CycleProfileCreateSerializer(data=request.data)
        if serializer.is_valid():
            profile = serializer.save(user=request.user)
            
            # Also create initial period log from the last period date
            PeriodLog.objects.create(
                user=request.user,
                period_start_date=profile.last_period_start_date,
                flow_intensity=profile.flow_intensity_last_period
            )
            
            return Response({
                "message": "Cycle profile created successfully",
                "profile": CycleProfileSerializer(profile).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        """Update entire cycle profile."""
        try:
            profile = CycleProfile.objects.get(user=request.user)
        except CycleProfile.DoesNotExist:
            return Response({
                "error": "No profile found. Use POST to create."
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CycleProfileSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated successfully",
                "profile": serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Partially update cycle profile."""
        try:
            profile = CycleProfile.objects.get(user=request.user)
        except CycleProfile.DoesNotExist:
            return Response({
                "error": "No profile found. Use POST to create."
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CycleProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated successfully",
                "profile": serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================================================
# 📅 PERIOD LOGGING
# =========================================================

class PeriodLogView(APIView):
    """
    API for logging periods.
    GET: List all period logs
    POST: Log a new period
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all period logs for user."""
        logs = PeriodLog.objects.filter(user=request.user).order_by('-period_start_date')
        serializer = PeriodLogSerializer(logs, many=True)
        
        return Response({
            "count": logs.count(),
            "period_logs": serializer.data
        })
    
    def post(self, request):
        """Log a new period."""
        serializer = PeriodLogCreateSerializer(data=request.data)
        if serializer.is_valid():
            period_log = serializer.save(user=request.user)
            
            # Update cycle profile's last period date
            try:
                profile = CycleProfile.objects.get(user=request.user)
                if period_log.period_start_date > profile.last_period_start_date:
                    profile.last_period_start_date = period_log.period_start_date
                    if period_log.flow_intensity:
                        profile.flow_intensity_last_period = period_log.flow_intensity
                    profile.save()
            except CycleProfile.DoesNotExist:
                pass
            
            return Response({
                "message": "Period logged successfully",
                "period_log": PeriodLogSerializer(period_log).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PeriodLogDetailView(APIView):
    """
    API for managing individual period log entries.
    GET: Get specific period log
    PUT: Update period log (e.g., add end date)
    DELETE: Remove period log
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, log_id):
        """Get specific period log."""
        try:
            log = PeriodLog.objects.get(id=log_id, user=request.user)
            serializer = PeriodLogSerializer(log)
            return Response(serializer.data)
        except PeriodLog.DoesNotExist:
            return Response({
                "error": "Period log not found"
            }, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request, log_id):
        """Update period log."""
        try:
            log = PeriodLog.objects.get(id=log_id, user=request.user)
        except PeriodLog.DoesNotExist:
            return Response({
                "error": "Period log not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = PeriodLogUpdateSerializer(log, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Period log updated successfully",
                "period_log": PeriodLogSerializer(log).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, log_id):
        """Delete period log."""
        try:
            log = PeriodLog.objects.get(id=log_id, user=request.user)
            log.delete()
            return Response({
                "message": "Period log deleted successfully"
            }, status=status.HTTP_204_NO_CONTENT)
        except PeriodLog.DoesNotExist:
            return Response({
                "error": "Period log not found"
            }, status=status.HTTP_404_NOT_FOUND)


# =========================================================
# 📝 DAILY CHECKIN
# =========================================================

class DailyCheckinView(APIView):
    """
    API for daily symptom and mood checkins.
    GET: Get checkins (with optional date filter)
    POST: Create or update today's checkin
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get daily checkins."""
        days = int(request.query_params.get('days', 30))
        start_date = date.today() - timedelta(days=days)
        
        checkins = DailyCheckin.objects.filter(
            user=request.user,
            checkin_date__gte=start_date
        ).order_by('-checkin_date')
        
        serializer = DailyCheckinSerializer(checkins, many=True)
        
        return Response({
            "period_days": days,
            "count": checkins.count(),
            "checkins": serializer.data
        })
    
    def post(self, request):
        """Create or update today's checkin."""
        checkin_date = request.data.get('checkin_date', date.today())
        if isinstance(checkin_date, str):
            checkin_date = datetime.strptime(checkin_date, "%Y-%m-%d").date()
        
        # Check if checkin already exists for this date
        existing = DailyCheckin.objects.filter(
            user=request.user,
            checkin_date=checkin_date
        ).first()
        
        if existing:
            # Update existing checkin
            serializer = DailyCheckinCreateSerializer(existing, data=request.data, partial=True)
            message = "Checkin updated successfully"
        else:
            # Create new checkin
            serializer = DailyCheckinCreateSerializer(data=request.data)
            message = "Checkin created successfully"
        
        if serializer.is_valid():
            checkin = serializer.save(user=request.user)
            
            # Calculate and set cycle day/phase
            try:
                profile = CycleProfile.objects.get(user=request.user)
                cycle_day = calculate_cycle_day(profile.last_period_start_date, checkin_date)
                phase_info = get_cycle_phase(
                    cycle_day, 
                    profile.average_cycle_length_days,
                    profile.average_period_length_days
                )
                checkin.cycle_day = cycle_day
                checkin.cycle_phase = phase_info['phase']
                checkin.save()
            except CycleProfile.DoesNotExist:
                pass
            
            return Response({
                "message": message,
                "checkin": DailyCheckinSerializer(checkin).data
            }, status=status.HTTP_201_CREATED if not existing else status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TodayCheckinView(APIView):
    """
    API to get today's checkin specifically.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get today's checkin if exists."""
        today = date.today()
        try:
            checkin = DailyCheckin.objects.get(user=request.user, checkin_date=today)
            return Response({
                "has_checkin_today": True,
                "checkin": DailyCheckinSerializer(checkin).data
            })
        except DailyCheckin.DoesNotExist:
            return Response({
                "has_checkin_today": False,
                "message": "No checkin recorded for today"
            })


# =========================================================
# 📊 CYCLE STATUS & DASHBOARD
# =========================================================

class CycleStatusView(APIView):
    """
    API to get current cycle status.
    Returns calculated cycle day, phase, predictions, etc.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current cycle status."""
        try:
            profile = CycleProfile.objects.get(user=request.user)
        except CycleProfile.DoesNotExist:
            return Response({
                "error": "No cycle profile found. Please complete onboarding first.",
                "has_profile": False
            }, status=status.HTTP_404_NOT_FOUND)
        
        status_data = get_cycle_status(
            profile.last_period_start_date,
            profile.average_cycle_length_days,
            profile.average_period_length_days
        )
        
        return Response({
            "has_profile": True,
            "current_cycle_status": status_data
        })


class CycleDashboardView(APIView):
    """
    Comprehensive cycle dashboard API.
    Returns the full JSON structure as specified in requirements.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get full cycle dashboard data."""
        try:
            profile = CycleProfile.objects.get(user=request.user)
        except CycleProfile.DoesNotExist:
            return Response({
                "error": "No cycle profile found. Please complete onboarding first.",
                "has_profile": False,
                "onboarding_required": True
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Prepare profile data dict
        profile_data = {
            'last_period_start_date': profile.last_period_start_date,
            'average_cycle_length_days': profile.average_cycle_length_days,
            'average_period_length_days': profile.average_period_length_days,
            'cycle_regularity': profile.cycle_regularity,
            'flow_intensity_last_period': profile.flow_intensity_last_period,
            'spotting_between_periods': profile.spotting_between_periods,
            'typical_pms_symptoms': profile.typical_pms_symptoms,
            'birth_control_status': profile.birth_control_status,
            'reproductive_status': profile.reproductive_status
        }
        
        # Get recent checkin
        recent_checkin = None
        try:
            latest_checkin = DailyCheckin.objects.filter(user=request.user).order_by('-checkin_date').first()
            if latest_checkin:
                recent_checkin = {
                    'mood': latest_checkin.mood,
                    'energy_level': latest_checkin.energy_level,
                    'physical_symptoms': latest_checkin.physical_symptoms,
                    'user_notes': latest_checkin.user_notes,
                    'checkin_date': latest_checkin.checkin_date.strftime('%Y-%m-%d')
                }
        except:
            pass
        
        # Get mood summary for insights
        mood_summary = None
        try:
            moods = MoodEntry.objects.filter(
                user=request.user,
                entry_date__gte=date.today() - timedelta(days=7)
            )
            if moods.exists():
                analysis = analyze_mood_entries(moods)
                mood_summary = analysis
        except:
            pass
        
        # Get period logs for irregularity analysis
        period_logs = list(PeriodLog.objects.filter(user=request.user).values(
            'period_start_date', 
            'period_end_date', 
            'cycle_length_from_previous',
            'actual_period_length'
        ))
        
        # Generate full dashboard
        dashboard = get_full_cycle_dashboard(
            profile_data,
            recent_checkin,
            mood_summary,
            period_logs if len(period_logs) >= 2 else None
        )
        
        return Response(dashboard)


# =========================================================
# 🧠 CYCLE INSIGHTS & PREDICTIONS
# =========================================================

class CycleInsightsView(APIView):
    """
    API for personalized cycle insights.
    Connects hormonal state with emotional patterns.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get personalized cycle insights."""
        try:
            profile = CycleProfile.objects.get(user=request.user)
        except CycleProfile.DoesNotExist:
            return Response({
                "error": "No cycle profile found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get current cycle status
        cycle_status = get_cycle_status(
            profile.last_period_start_date,
            profile.average_cycle_length_days,
            profile.average_period_length_days
        )
        
        # Get mood data
        mood_data = None
        moods = MoodEntry.objects.filter(
            user=request.user,
            entry_date__gte=date.today() - timedelta(days=7)
        )
        if moods.exists():
            mood_data = analyze_mood_entries(moods)
        
        # Get recent checkin
        checkin_data = None
        latest_checkin = DailyCheckin.objects.filter(user=request.user).order_by('-checkin_date').first()
        if latest_checkin:
            checkin_data = {
                'mood': latest_checkin.mood,
                'energy_level': latest_checkin.energy_level,
                'physical_symptoms': latest_checkin.physical_symptoms
            }
        
        # Generate insights
        insights = generate_personalized_insights(cycle_status, mood_data, checkin_data)
        
        return Response({
            "cycle_status": cycle_status,
            "insights": insights
        })


class CycleIrregularityView(APIView):
    """
    API to check for cycle irregularities.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Analyze cycle irregularities."""
        try:
            profile = CycleProfile.objects.get(user=request.user)
        except CycleProfile.DoesNotExist:
            return Response({
                "error": "No cycle profile found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get period logs
        period_logs = list(PeriodLog.objects.filter(user=request.user).values(
            'period_start_date',
            'cycle_length_from_previous',
            'actual_period_length'
        ))
        
        if len(period_logs) < 2:
            return Response({
                "has_sufficient_data": False,
                "message": "Need at least 2 period records for irregularity analysis",
                "periods_logged": len(period_logs)
            })
        
        analysis = detect_irregularity(period_logs, profile.average_cycle_length_days)
        
        return Response({
            "has_sufficient_data": True,
            "analysis": analysis
        })


# =========================================================
# 🌸 CYCLE CALENDAR DATA
# =========================================================

class CycleCalendarView(APIView):
    """
    API to get cycle data for calendar visualization.
    Returns period days, fertile windows, and predictions for a given month.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get calendar data for cycle visualization."""
        # Get month/year from params (default to current month)
        year = int(request.query_params.get('year', date.today().year))
        month = int(request.query_params.get('month', date.today().month))
        
        try:
            profile = CycleProfile.objects.get(user=request.user)
        except CycleProfile.DoesNotExist:
            return Response({
                "error": "No cycle profile found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get actual period logs for this time range
        start_of_month = date(year, month, 1)
        if month == 12:
            end_of_month = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = date(year, month + 1, 1) - timedelta(days=1)
        
        period_logs = PeriodLog.objects.filter(
            user=request.user,
            period_start_date__lte=end_of_month,
        ).filter(
            # Either period starts in this month or extends into it
            period_start_date__gte=start_of_month - timedelta(days=10)
        )
        
        # Build calendar data
        calendar_data = {
            "year": year,
            "month": month,
            "period_days": [],
            "predicted_period_days": [],
            "fertile_days": [],
            "ovulation_days": [],
            "pms_days": []
        }
        
        # Add actual logged period days
        for log in period_logs:
            start = log.period_start_date
            end = log.period_end_date or (start + timedelta(days=profile.average_period_length_days - 1))
            
            current = start
            while current <= end:
                if start_of_month <= current <= end_of_month:
                    calendar_data["period_days"].append(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)
        
        # Calculate predictions
        last_period = profile.last_period_start_date
        cycle_length = profile.average_cycle_length_days
        period_length = profile.average_period_length_days
        
        # Generate predictions for this month
        predicted_period = last_period
        while predicted_period < end_of_month:
            predicted_period = predicted_period + timedelta(days=cycle_length)
            
            if predicted_period >= start_of_month and predicted_period <= end_of_month:
                # Add predicted period days
                for i in range(period_length):
                    day = predicted_period + timedelta(days=i)
                    if start_of_month <= day <= end_of_month:
                        day_str = day.strftime("%Y-%m-%d")
                        if day_str not in calendar_data["period_days"]:
                            calendar_data["predicted_period_days"].append(day_str)
                
                # Add ovulation day (14 days before next predicted period)
                ovulation = predicted_period - timedelta(days=14)
                if start_of_month <= ovulation <= end_of_month:
                    calendar_data["ovulation_days"].append(ovulation.strftime("%Y-%m-%d"))
                
                # Add fertile window (5 days before ovulation + ovulation)
                for i in range(6):
                    fertile_day = ovulation - timedelta(days=5-i)
                    if start_of_month <= fertile_day <= end_of_month:
                        calendar_data["fertile_days"].append(fertile_day.strftime("%Y-%m-%d"))
                
                # Add PMS days (7 days before period)
                for i in range(7):
                    pms_day = predicted_period - timedelta(days=i+1)
                    if start_of_month <= pms_day <= end_of_month:
                        calendar_data["pms_days"].append(pms_day.strftime("%Y-%m-%d"))
        
        return Response(calendar_data)


# =========================================================
# 🎯 ONBOARDING STATUS CHECK
# =========================================================

class OnboardingStatusView(APIView):
    """
    API to check if user has completed cycle onboarding.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Check onboarding status."""
        try:
            profile = CycleProfile.objects.get(user=request.user)
            return Response({
                "has_profile": True,
                "is_onboarding_complete": profile.is_onboarding_complete,
                "profile_created_at": profile.created_at,
                "last_updated": profile.updated_at
            })
        except CycleProfile.DoesNotExist:
            return Response({
                "has_profile": False,
                "is_onboarding_complete": False,
                "message": "User needs to complete cycle setup onboarding"
            })


# =========================================================
# 📋 CYCLE OPTIONS (For Frontend Dropdowns)
# =========================================================

@api_view(["GET"])
@permission_classes([AllowAny])
def cycle_options(request):
    """
    Returns all available options for cycle-related dropdowns.
    Useful for frontend form building.
    """
    return Response({
        "cycle_length_options": [
            {"value": "21-24", "label": "21-24 days"},
            {"value": "25-28", "label": "25-28 days"},
            {"value": "29-32", "label": "29-32 days"},
            {"value": "33-35", "label": "33-35 days"},
            {"value": "35+", "label": "More than 35 days"},
            {"value": "not_sure", "label": "Not sure"}
        ],
        "period_length_options": [
            {"value": "2-3", "label": "2-3 days"},
            {"value": "3-4", "label": "3-4 days"},
            {"value": "5-6", "label": "5-6 days"},
            {"value": "7+", "label": "7+ days"},
            {"value": "not_sure", "label": "Not sure"}
        ],
        "regularity_options": [
            {"value": "mostly_regular", "label": "Yes, mostly regular"},
            {"value": "sometimes_irregular", "label": "Sometimes irregular"},
            {"value": "very_unpredictable", "label": "Very unpredictable"},
            {"value": "not_sure", "label": "Not sure"}
        ],
        "flow_intensity_options": [
            {"value": "light", "label": "Light"},
            {"value": "moderate", "label": "Moderate"},
            {"value": "heavy", "label": "Heavy"},
            {"value": "very_heavy", "label": "Very heavy"},
            {"value": "not_sure", "label": "Not sure"}
        ],
        "spotting_options": [
            {"value": "never", "label": "Never"},
            {"value": "occasionally", "label": "Occasionally"},
            {"value": "frequently", "label": "Frequently"},
            {"value": "not_sure", "label": "Not sure"}
        ],
        "pms_symptom_options": [
            {"value": "mood_swings", "label": "Mood swings"},
            {"value": "irritability", "label": "Irritability"},
            {"value": "anxiety", "label": "Anxiety"},
            {"value": "low_mood", "label": "Low mood"},
            {"value": "bloating", "label": "Bloating"},
            {"value": "breast_tenderness", "label": "Breast tenderness"},
            {"value": "headache", "label": "Headache"},
            {"value": "fatigue", "label": "Fatigue"},
            {"value": "cramps", "label": "Cramps"},
            {"value": "acne", "label": "Acne"},
            {"value": "sleep_disturbance", "label": "Sleep disturbance"},
            {"value": "no_symptoms", "label": "No noticeable symptoms"},
            {"value": "not_sure", "label": "Not sure"}
        ],
        "birth_control_options": [
            {"value": "no", "label": "No"},
            {"value": "pill", "label": "Yes – Pill"},
            {"value": "hormonal_iud", "label": "Yes – Hormonal IUD"},
            {"value": "copper_iud", "label": "Yes – Copper IUD"},
            {"value": "patch_ring", "label": "Yes – Patch / Ring"},
            {"value": "prefer_not_say", "label": "Prefer not to say"}
        ],
        "reproductive_status_options": [
            {"value": "none", "label": "None"},
            {"value": "trying_to_conceive", "label": "Trying to conceive"},
            {"value": "pregnant", "label": "Pregnant"},
            {"value": "postpartum", "label": "Postpartum"},
            {"value": "prefer_not_say", "label": "Prefer not to say"}
        ],
        "mood_options": [
            {"value": "calm", "label": "Calm"},
            {"value": "happy", "label": "Happy"},
            {"value": "irritated", "label": "Irritated"},
            {"value": "anxious", "label": "Anxious"},
            {"value": "emotional", "label": "Emotional"},
            {"value": "low", "label": "Low"},
            {"value": "motivated", "label": "Motivated"},
            {"value": "overwhelmed", "label": "Overwhelmed"}
        ],
        "energy_level_options": [
            {"value": "very_low", "label": "Very low"},
            {"value": "low", "label": "Low"},
            {"value": "moderate", "label": "Moderate"},
            {"value": "high", "label": "High"}
        ],
        "physical_symptom_options": [
            {"value": "cramps", "label": "Cramps"},
            {"value": "headache", "label": "Headache"},
            {"value": "bloating", "label": "Bloating"},
            {"value": "breast_tenderness", "label": "Breast tenderness"},
            {"value": "fatigue", "label": "Fatigue"},
            {"value": "acne", "label": "Acne"},
            {"value": "back_pain", "label": "Back pain"},
            {"value": "nausea", "label": "Nausea"},
            {"value": "no_symptoms", "label": "No symptoms"}
        ]
    })