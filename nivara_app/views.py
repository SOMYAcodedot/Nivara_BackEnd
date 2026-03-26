from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Count, StdDev
from django.db.models.functions import TruncDate, TruncWeek
from django.core.cache import cache
from collections import Counter
import json
import re
from datetime import datetime, timedelta, date

from .models import (
    MoodEntry,
    CycleEntry,
    CycleProfile,
    PeriodLog,
    DailyCheckin,
    Hospital,
    Doctor,
    DoctorConsultationBooking,
    Payment,
    ChatSession,
    ChatMessage,
)
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
    DailyCheckinCreateSerializer,
    UserProfileSerializer,
    UserProfileSetupSerializer,
    UserProfileBasicSerializer,
    HospitalSerializer,
    DoctorSerializer,
    DoctorListSerializer,
    DoctorConsultationBookingSerializer,
    DoctorConsultationBookingCreateSerializer,
    PaymentSerializer,
    PaymentInitiateSerializer,
    PaymentConfirmSerializer,
)

User = get_user_model()

# AI ENGINE IMPORTS
from .ai_engine.mood_analysis import analyze_mood_entries
from .ai_engine.chatbot_engine import chatbot_response
# generic_chat imports openai — lazy-load inside _nivara_single_llm_turn so runserver works if venv missing openai
from .ai_engine.cycle_logic import (
    predict_cycle, 
    get_cycle_status, 
    get_full_cycle_dashboard,
    calculate_cycle_day,
    get_cycle_phase,
    detect_irregularity,
    generate_personalized_insights
)
from .ai_engine.lifestyle_ai import generate_lifestyle_plan, generate_lifestyle_recommendations
from .ai_engine.report_generator import generate_health_report, generate_health_summary_report
from .ai_engine.analysis import analyze_lifestyle_report_bundle, analyze_user_wellness


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
        from .db_retry import sqlite_write
        from django.db import OperationalError

        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""

        if not username or not password:
            return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        def _do_login():
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return (status.HTTP_404_NOT_FOUND, {"error": "User not found"})
            authenticated_user = authenticate(username=username, password=password)
            if not authenticated_user:
                return (status.HTTP_401_UNAUTHORIZED, {"error": "Invalid credentials"})
            refresh = RefreshToken.for_user(authenticated_user)
            return (status.HTTP_200_OK, {
                "message": "Login successful",
                "user": {
                    "id": authenticated_user.id,
                    "username": authenticated_user.username,
                    "email": authenticated_user.email,
                },
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            })

        try:
            status_code, data = sqlite_write(_do_login)
            return Response(data, status=status_code)
        except OperationalError:
            return Response(
                {"error": "Database busy, please try again in a moment."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Login failed")
            return Response(
                {"error": "Server error during login. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
# 👤 USER PROFILE (STEP 1 - One-Time Setup)
# =========================================================

class UserProfileView(APIView):
    """
    API for user profile management.
    GET: Retrieve current user profile
    PUT/PATCH: Update/setup user profile (STEP 1)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user profile with all details."""
        serializer = UserProfileSerializer(request.user)
        return Response({
            "user_profile": serializer.data
        })
    
    def put(self, request):
        """Complete initial profile setup (STEP 1)."""
        serializer = UserProfileSetupSerializer(request.user, data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            return Response({
                "message": "Profile setup completed successfully",
                "user_profile": UserProfileSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Partially update user profile."""
        serializer = UserProfileSetupSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            
            return Response({
                "message": "Profile updated successfully",
                "user_profile": UserProfileSerializer(user).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileStatusView(APIView):
    """
    Check if user has completed profile setup.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Check profile completion status."""
        user = request.user
        
        return Response({
            "is_profile_complete": user.is_profile_complete,
            "profile_completed_at": user.profile_completed_at,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def lifestyle_options(request):
    """
    Returns lifestyle dropdown options for frontend.
    """
    return Response({
        "lifestyle_options": [
            {"value": "student", "label": "Student"},
            {"value": "working", "label": "Working Professional"},
            {"value": "homemaker", "label": "Homemaker"},
            {"value": "retired", "label": "Retired"},
            {"value": "other", "label": "Other"}
        ]
    })


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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mood_insights_ai(request):
    """
    Mood Tracker — Insights tab: one LLM call (analyze_user_wellness) using the same
    aggregated payload as lifestyle/report (_build_wellness_llm_payload).
    Query params: days (default 30), aligned with mood/summary and chart APIs.
    """
    days = int(request.query_params.get("days", 30))
    user = request.user
    payload = _build_wellness_llm_payload(user, days=days)
    llm_result = _get_wellness_llm_analysis(user, days=days, payload=payload)

    body = {
        "source": "ai_engine",
        "generated_by": "Nivara analysis.py — analyze_user_wellness",
        "period_days": days,
        "llm_generated": llm_result.get("status") == "success",
        "emotional_analysis": "",
        "care_recommendations": [],
        "footnote": {
            "total_entries": payload["mood_summary"].get("total_entries", 0),
            "period_days": days,
        },
        "highlights": {},
    }
    if llm_result.get("status") == "success":
        analysis = llm_result["analysis"]
        body["emotional_analysis"] = _compose_emotional_analysis(analysis)
        body["care_recommendations"] = _flatten_care_recommendations(analysis)
        body["highlights"] = analysis.get("highlights") or {}
    else:
        body["error"] = llm_result.get("message")
        body["details"] = llm_result.get("details")

    return Response(body)


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
# 🌿 PHASE 4: LIFESTYLE INTELLIGENCE (AI Recommendation Engine)
# Inputs: mood analysis, cycle phase, stress level → Yoga, Diet, Sleep, Emotional tips
# =========================================================

def _build_mood_context_for_lifestyle(request_user, days=30):
    """Build mood_analysis_result and stress_level for Phase 4 from user's mood data."""
    start_date = date.today() - timedelta(days=days)
    moods = MoodEntry.objects.filter(user=request_user, entry_date__gte=start_date)
    total = moods.count()
    
    if total == 0:
        return {
            "mood_analysis_result": {"average_mood": 5, "dominant_emotion": "neutral", "trend": "Stable"},
            "stress_level": "Unknown"
        }
    
    avg_mood = round(moods.aggregate(avg=Avg('mood_score'))['avg'] or 5, 1)
    emotion_counts = moods.values('emotion_type').annotate(count=Count('id')).order_by('-count')
    dominant_emotion = emotion_counts[0]['emotion_type'] if emotion_counts else "neutral"
    
    # Trend: compare first half vs second half of period
    mid = start_date + timedelta(days=days // 2)
    first_half = moods.filter(entry_date__lt=mid).aggregate(avg=Avg('mood_score'))['avg'] or 5
    second_half = moods.filter(entry_date__gte=mid).aggregate(avg=Avg('mood_score'))['avg'] or 5
    if second_half > first_half + 0.5:
        trend = "Improving"
    elif second_half < first_half - 0.5:
        trend = "Declining"
    else:
        trend = "Stable"
    
    # Stress (same logic as mood_analytics_summary)
    stress_emotions = ['anxious', 'stressed', 'irritated', 'overwhelmed', 'tired', 'sad']
    stress_count = moods.filter(emotion_type__in=stress_emotions).count()
    stress_percentage = (stress_count / total) * 100
    journal_stress_total = 0
    entries_with_journal = 0
    for m in moods:
        if m.journal_text:
            entries_with_journal += 1
            journal_stress_total += calculate_stress_from_journal(m.journal_text)
    avg_journal_stress = journal_stress_total / entries_with_journal if entries_with_journal > 0 else 0
    combined_stress = (stress_percentage * 0.6) + (avg_journal_stress * 4)
    if combined_stress < 20:
        stress_level = "Low"
    elif combined_stress < 40:
        stress_level = "Moderate"
    elif combined_stress < 60:
        stress_level = "High"
    else:
        stress_level = "Very High"
    
    mood_analysis_result = {
        "average_mood": avg_mood,
        "dominant_emotion": dominant_emotion,
        "trend": trend,
        "stress_percentage": round(stress_percentage, 1),
    }
    return {"mood_analysis_result": mood_analysis_result, "stress_level": stress_level}


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def lifestyle_recommendations(request):
    """
    Phase 4: Lifestyle Intelligence API.
    Returns structured recommendations: yoga, diet, sleep, emotional regulation.
    Uses mood analysis, cycle phase, and stress level (all derived from user data).
    Query params: days (default 30) for mood window.
    """
    days = int(request.query_params.get("days", 30))
    user = request.user
    
    # 1) Mood context + stress level
    mood_ctx = _build_mood_context_for_lifestyle(user, days=days)
    mood_analysis_result = mood_ctx["mood_analysis_result"]
    stress_level = mood_ctx["stress_level"]
    
    # 2) Cycle phase (Phase 3: CycleProfile + get_cycle_status)
    cycle_phase_info = None
    try:
        profile = CycleProfile.objects.get(user=user)
        cycle_phase_info = get_cycle_status(
            profile.last_period_start_date,
            profile.average_cycle_length_days,
            profile.average_period_length_days
        )
    except CycleProfile.DoesNotExist:
        pass
    
    # 3) LLM bundle (cached; shares one Azure call with health report) or rule-based fallback
    compiled = _build_health_summary_compiled_data(user, days=days)
    bundle = _get_llm_lifestyle_report_bundle(user, days=days, compiled=compiled)
    llm_generated = (
        bundle.get("status") == "success" and bundle.get("lifestyle") is not None
    )
    if llm_generated:
        recommendations = bundle["lifestyle"]
    else:
        recommendations = generate_lifestyle_recommendations(
            mood_analysis_result, cycle_phase_info, stress_level
        )

    # 4) Build context for frontend ("Based on: ...")
    context = {
        "mood_analysis": mood_analysis_result,
        "cycle_phase": cycle_phase_info,
        "stress_level": stress_level,
        "period_days": days,
    }

    return Response({
        "source": "ai_engine",
        "generated_by": "Nivara analysis engine (Azure OpenAI via analysis.py)",
        "message": (
            "Recommendations from a single LLM pass over your mood, cycle, and report context "
            "when available; otherwise rule-based templates."
        ),
        "context": context,
        "recommendations": recommendations,
        "llm_generated": llm_generated,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def lifestyle_recommendations_context(request):
    """
    Phase 4: Get only the context (mood, cycle phase, stress) without recommendations.
    Useful for displaying "Based on your current context" before loading full recommendations.
    Query params: days (default 30).
    """
    days = int(request.query_params.get("days", 30))
    user = request.user
    
    mood_ctx = _build_mood_context_for_lifestyle(user, days=days)
    cycle_phase_info = None
    try:
        profile = CycleProfile.objects.get(user=user)
        cycle_phase_info = get_cycle_status(
            profile.last_period_start_date,
            profile.average_cycle_length_days,
            profile.average_period_length_days
        )
    except CycleProfile.DoesNotExist:
        pass
    
    return Response({
        "source": "ai_engine",
        "message": "Context is derived from the AI-engine model (mood analysis, cycle phase, stress level).",
        "mood_analysis": mood_ctx["mood_analysis_result"],
        "cycle_phase": cycle_phase_info,
        "stress_level": mood_ctx["stress_level"],
        "period_days": days,
    })


# =========================================================
# 📊 HEALTH REPORT GENERATOR (Legacy)
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
# 🌸 PHASE 6: AI HEALTH REPORT GENERATOR (Generate Health Summary)
# Compiles: mood statistics, cycle patterns, stress markers, lifestyle consistency
# Returns: professional report, risk flags, suggestions, summary insights
# =========================================================

def _build_health_summary_compiled_data(user, days=30):
    """Compile mood stats, cycle patterns, stress markers, lifestyle consistency for Phase 6 report."""
    start_date = date.today() - timedelta(days=days)
    moods = MoodEntry.objects.filter(user=user, entry_date__gte=start_date)
    total_entries = moods.count()

    # --- Mood statistics (aligned with Phase 2 summary) ---
    mood_ctx = _build_mood_context_for_lifestyle(user, days=days)
    mood_result = mood_ctx["mood_analysis_result"]
    mood_statistics = {
        "average_mood": mood_result.get("average_mood"),
        "dominant_emotion": mood_result.get("dominant_emotion"),
        "trend": mood_result.get("trend"),
        "stress_percentage": mood_result.get("stress_percentage"),
        "total_entries": total_entries,
        "period_days": days,
    }
    if total_entries > 1:
        mood_scores = list(moods.values_list("mood_score", flat=True))
        mean = sum(mood_scores) / len(mood_scores)
        variance = sum((x - mean) ** 2 for x in mood_scores) / len(mood_scores)
        std_dev = variance ** 0.5
        max_std = 4.5
        mood_statistics["mood_stability_index"] = round(max(0, 100 - (std_dev / max_std * 100)), 1)
    else:
        mood_statistics["mood_stability_index"] = None

    # --- Stress markers ---
    stress_level = mood_ctx["stress_level"]
    stress_markers = {
        "stress_level": stress_level,
        "stress_percentage": mood_result.get("stress_percentage"),
        "markers": [],
        "summary_note": f"Stress level is {stress_level} over the last {days} days.",
    }
    if stress_level in ("High", "Very High"):
        stress_markers["markers"] = ["Elevated stress-related emotions", "Consider stress-management focus"]

    # --- Cycle patterns (Phase 3: profile + status + irregularity) ---
    cycle_patterns = None
    try:
        profile = CycleProfile.objects.get(user=user)
        status_data = get_cycle_status(
            profile.last_period_start_date,
            profile.average_cycle_length_days,
            profile.average_period_length_days,
        )
        period_logs = list(
            PeriodLog.objects.filter(user=user).values(
                "period_start_date", "cycle_length_from_previous", "actual_period_length"
            )
        )
        irregularity = detect_irregularity(period_logs, profile.average_cycle_length_days) if len(period_logs) >= 2 else {}
        cycle_patterns = {
            "cycle_phase": status_data.get("cycle_phase"),
            "phase_display": status_data.get("phase_display"),
            "cycle_day": status_data.get("cycle_day"),
            "pms_window": status_data.get("pms_window"),
            "regularity_message": irregularity.get("regularity_message"),
            "regularity_status": irregularity.get("regularity_status"),
            "irregularity_analysis": irregularity if irregularity.get("has_data") else None,
        }
    except CycleProfile.DoesNotExist:
        pass

    # --- Lifestyle consistency ---
    mood_logging_consistency = "high" if total_entries >= 20 else ("medium" if total_entries >= 7 else "low")
    sleep_note = None
    if getattr(user, "sleep_average", None) is not None:
        sleep_note = f"Profile sleep quality average: {user.sleep_average}/10."
    lifestyle_consistency = {
        "mood_logging_consistency": mood_logging_consistency,
        "sleep_note": sleep_note,
        "profile_complete": getattr(user, "is_profile_complete", False),
        "consistency_summary": f"Mood logging consistency: {mood_logging_consistency}. " + (sleep_note or "Complete profile for sleep insights."),
    }

    return {
        "mood_statistics": mood_statistics,
        "cycle_patterns": cycle_patterns,
        "stress_markers": stress_markers,
        "lifestyle_consistency": lifestyle_consistency,
    }


def _compact_report_for_llm(compiled: dict) -> dict:
    """Small factual dict for the LLM (keeps token use down)."""
    mood = compiled.get("mood_statistics") or {}
    stress = compiled.get("stress_markers") or {}
    cycle = compiled.get("cycle_patterns") or {}
    life = compiled.get("lifestyle_consistency") or {}
    ir = (cycle.get("irregularity_analysis") or {}) if cycle else {}
    return {
        "average_mood": mood.get("average_mood"),
        "dominant_emotion": mood.get("dominant_emotion"),
        "trend": mood.get("trend"),
        "total_entries": mood.get("total_entries"),
        "mood_stability_index": mood.get("mood_stability_index"),
        "stress_level": stress.get("stress_level"),
        "stress_percentage": stress.get("stress_percentage"),
        "cycle_phase": cycle.get("cycle_phase") or cycle.get("phase_display"),
        "phase_display": cycle.get("phase_display"),
        "cycle_day": cycle.get("cycle_day"),
        "pms_window": cycle.get("pms_window"),
        "cycle_regularity_note": ir.get("regularity_message"),
        "mood_logging_consistency": life.get("mood_logging_consistency"),
        "sleep_note": life.get("sleep_note"),
    }


def _build_wellness_llm_payload(request_user, days=30):
    """
    Build the aggregated payload expected by nivara_app.ai_engine.analysis.validate_payload.
    """
    start_date = date.today() - timedelta(days=days)
    moods = MoodEntry.objects.filter(user=request_user, entry_date__gte=start_date)
    total_entries = moods.count()

    stress_emotions = [
        "anxious",
        "stressed",
        "irritated",
        "overwhelmed",
        "tired",
        "sad",
    ]

    if total_entries == 0:
        avg_mood = 5.0
        dominant_emotion = "neutral"
        stress_level = "Unknown"
        stress_pct = 0.0
        weekly_variation = 0.0
        stability_index = 50.0
        emotional_variance = 0.0
    else:
        avg_mood = round(moods.aggregate(avg=Avg("mood_score"))["avg"] or 5, 1)
        emotion_counts = moods.values("emotion_type").annotate(c=Count("id")).order_by("-c")
        dominant_emotion = emotion_counts[0]["emotion_type"] if emotion_counts else "neutral"
        stress_count = moods.filter(emotion_type__in=stress_emotions).count()
        stress_pct = round((stress_count / total_entries) * 100, 1)
        journal_stress_total = 0
        entries_with_journal = 0
        for m in moods:
            if m.journal_text:
                entries_with_journal += 1
                journal_stress_total += calculate_stress_from_journal(m.journal_text)
        avg_journal_stress = (
            journal_stress_total / entries_with_journal if entries_with_journal > 0 else 0
        )
        combined_stress = (stress_pct * 0.6) + (avg_journal_stress * 4)
        if combined_stress < 20:
            stress_level = "Low"
        elif combined_stress < 40:
            stress_level = "Moderate"
        elif combined_stress < 60:
            stress_level = "High"
        else:
            stress_level = "Very High"
        mood_scores = list(moods.values_list("mood_score", flat=True))
        if len(mood_scores) > 1:
            mean = sum(mood_scores) / len(mood_scores)
            variance = sum((x - mean) ** 2 for x in mood_scores) / len(mood_scores)
            weekly_variation = round(variance**0.5, 1)
        else:
            weekly_variation = 0.0
        max_possible_std = 4.5
        stability_index = round(
            max(0, 100 - (weekly_variation / max_possible_std * 100)), 1
        )
        emotional_variance = weekly_variation

    mood_summary = {
        "period_days": days,
        "total_entries": total_entries,
        "average_mood": avg_mood,
        "dominant_emotion": dominant_emotion,
        "stress_level": stress_level,
        "stress_percentage": stress_pct,
        "weekly_variation": weekly_variation,
        "mood_stability_index": stability_index,
        "emotional_variance": emotional_variance,
    }

    daily_data = (
        moods.values("entry_date")
        .annotate(avg_mood=Avg("mood_score"), entries_count=Count("id"))
        .order_by("entry_date")
    )
    trend_data = [
        {
            "date": entry["entry_date"].strftime("%Y-%m-%d"),
            "mood_score": round(entry["avg_mood"], 1) if entry["avg_mood"] else 0,
            "entries": entry["entries_count"],
        }
        for entry in daily_data
    ]
    mood_trend = {
        "period_days": days,
        "data_points": len(trend_data),
        "trend_data": trend_data,
    }

    if total_entries == 0:
        emotion_distribution = {
            "period_days": days,
            "total_entries": 0,
            "distribution": [],
            "category_breakdown": {"positive": 0.0, "negative": 0.0, "neutral": 0.0},
        }
    else:
        emotion_rows = moods.values("emotion_type").annotate(count=Count("id")).order_by("-count")
        distribution = [
            {
                "emotion": row["emotion_type"],
                "count": row["count"],
                "percentage": round((row["count"] / total_entries) * 100, 1),
            }
            for row in emotion_rows
        ]
        category_counts = {"positive": 0, "negative": 0, "neutral": 0}
        for row in emotion_rows:
            category = get_emotion_category(row["emotion_type"])
            category_counts[category] += row["count"]
        category_breakdown = {
            k: round((v / total_entries) * 100, 1) for k, v in category_counts.items()
        }
        emotion_distribution = {
            "period_days": days,
            "total_entries": total_entries,
            "distribution": distribution,
            "category_breakdown": category_breakdown,
        }

    weekly_data = moods.annotate(week=TruncWeek("entry_date")).values("week").annotate(
        total_entries=Count("id"), avg_mood=Avg("mood_score")
    ).order_by("week")
    stress_by_week = []
    for week_entry in weekly_data:
        week_start = week_entry["week"]
        week_end = week_start + timedelta(days=7)
        week_moods = moods.filter(entry_date__gte=week_start, entry_date__lt=week_end)
        stress_emotion_count = week_moods.filter(
            emotion_type__in=stress_emotions
        ).count()
        journal_stress = 0
        for mood in week_moods:
            if mood.journal_text:
                journal_stress += calculate_stress_from_journal(mood.journal_text)
        total_w = week_entry["total_entries"]
        spct = round((stress_emotion_count / total_w) * 100, 1) if total_w > 0 else 0
        stress_by_week.append(
            {
                "week_start": week_start.strftime("%Y-%m-%d"),
                "total_entries": total_w,
                "stress_emotion_count": stress_emotion_count,
                "stress_percentage": spct,
                "journal_stress_score": journal_stress,
                "avg_mood": round(week_entry["avg_mood"], 1) if week_entry["avg_mood"] else 0,
            }
        )
    keyword_frequency = Counter()
    for mood in moods:
        if mood.journal_text:
            text_lower = mood.journal_text.lower()
            for keyword in STRESS_KEYWORDS:
                if keyword in text_lower:
                    keyword_frequency[keyword] += 1
    top_stress_keywords = [
        {"keyword": k, "count": v} for k, v in keyword_frequency.most_common(10)
    ]
    stress_analysis = {
        "period_days": days,
        "weekly_stress_data": stress_by_week,
        "top_stress_keywords": top_stress_keywords,
    }

    entries = []
    for m in moods.order_by("-entry_date", "-created_at")[:45]:
        entries.append(
            {
                "mood_score": m.mood_score,
                "emotion_type": m.emotion_type,
                "journal_text": (m.journal_text or "")[:500],
                "entry_date": m.entry_date.strftime("%Y-%m-%d"),
            }
        )
    recent_mood_entries = {"period_days": days, "count": len(entries), "entries": entries}

    try:
        profile = CycleProfile.objects.get(user=request_user)
        cycle_status = get_cycle_status(
            profile.last_period_start_date,
            profile.average_cycle_length_days,
            profile.average_period_length_days,
        )
    except CycleProfile.DoesNotExist:
        cycle_status = {
            "cycle_day": 1,
            "cycle_phase": "follicular",
            "phase_display": "Cycle profile not set",
            "phase_description": "Complete cycle onboarding for accurate phase-based tips.",
            "energy_level": "moderate",
            "hormone_status": "Unknown without cycle profile",
            "days_until_next_period": None,
            "predicted_next_period": None,
            "pms_window": False,
            "fertile_window": None,
            "is_fertile_today": False,
        }

    return {
        "mood_summary": mood_summary,
        "mood_trend": mood_trend,
        "emotion_distribution": emotion_distribution,
        "stress_analysis": stress_analysis,
        "recent_mood_entries": recent_mood_entries,
        "cycle_status": cycle_status,
    }


def _compose_emotional_analysis(analysis):
    """One paragraph for Mood Insights from analyze_user_wellness."""
    if not isinstance(analysis, dict):
        return ""
    cs = analysis.get("current_status") or {}
    parts = [
        cs.get("emotional_overview"),
        cs.get("stability_insight"),
        cs.get("stress_reflection"),
        cs.get("cycle_mood_connection"),
        cs.get("overall_interpretation"),
    ]
    return " ".join(p.strip() for p in parts if p and str(p).strip())


def _flatten_care_recommendations(analysis):
    """Flatten recommendation groups into a short list for the Mood UI."""
    if not isinstance(analysis, dict):
        return []
    rec = analysis.get("recommendations") or {}
    out = []
    for key in (
        "emotional_support",
        "lifestyle_suggestions",
        "stress_management",
        "cycle_phase_tips",
    ):
        items = rec.get(key)
        if isinstance(items, list):
            for x in items:
                if x is not None and str(x).strip():
                    out.append(str(x).strip())
    ga = rec.get("gentle_advice")
    if ga and str(ga).strip():
        out.append(str(ga).strip())
    seen = set()
    unique = []
    for x in out:
        if x not in seen:
            seen.add(x)
            unique.append(x)
    return unique[:12]


def _get_wellness_llm_analysis(request_user, days=30, payload=None):
    """Single analyze_user_wellness LLM call; cached 10 minutes per user/days."""
    cache_key = f"nivara_wellness_analysis_{request_user.id}_{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    if payload is None:
        payload = _build_wellness_llm_payload(request_user, days=days)
    out = analyze_user_wellness(payload)
    if out.get("status") == "success":
        cache.set(cache_key, out, timeout=600)
    return out


def _shape_cycle_llm_insights(llm_result, regularity):
    """Map analyze_user_wellness output to cycle insights UI fields."""
    base = {
        "personalized_insights": "",
        "mood_cycle_connection": "",
        "cycle_regularity_narrative": "",
        "alerts": [],
        "phase_tips": {
            "menstrual": "",
            "follicular": "",
            "ovulation": "",
            "luteal": "",
        },
    }
    if llm_result.get("status") != "success":
        base["error"] = llm_result.get("message")
        return base

    analysis = llm_result.get("analysis") or {}
    cs = analysis.get("current_status") or {}
    rec = analysis.get("recommendations") or {}
    hl = analysis.get("highlights") or {}

    tips = rec.get("cycle_phase_tips")
    if not isinstance(tips, list):
        tips = []
    phase_order = ["menstrual", "follicular", "ovulation", "luteal"]
    for i, phase in enumerate(phase_order):
        if i < len(tips) and tips[i]:
            base["phase_tips"][phase] = str(tips[i]).strip()

    base["personalized_insights"] = " ".join(
        p
        for p in [cs.get("emotional_overview"), cs.get("overall_interpretation")]
        if p and str(p).strip()
    ).strip()
    base["mood_cycle_connection"] = (cs.get("cycle_mood_connection") or "").strip()

    reg_msg = (regularity or {}).get("regularity_message") if isinstance(regularity, dict) else ""
    stability = (cs.get("stability_insight") or "").strip()
    positive = (hl.get("positive_pattern") or "").strip()
    base["cycle_regularity_narrative"] = " ".join(
        p for p in [reg_msg, stability, positive] if p
    ).strip()

    alerts = []
    for key in ("watch_out_for", "energy_note"):
        v = hl.get(key)
        if v and str(v).strip():
            alerts.append(str(v).strip())
    sr = cs.get("stress_reflection")
    if sr and str(sr).strip():
        alerts.append(str(sr).strip())
    base["alerts"] = alerts[:6]
    return base


def _get_llm_lifestyle_report_bundle(request_user, days=30, compiled=None):
    """
    One Azure completion → lifestyle cards + report narrative; cached 10 minutes per user/days.
    """
    cache_key = f"nivara_llm_bundle_{request_user.id}_{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if compiled is None:
        compiled = _build_health_summary_compiled_data(request_user, days=days)
    payload = _build_wellness_llm_payload(request_user, days=days)
    report_ctx = _compact_report_for_llm(compiled)
    bundle = analyze_lifestyle_report_bundle(payload, report_context=report_ctx)
    if bundle.get("status") == "success":
        cache.set(cache_key, bundle, timeout=600)
    return bundle


def _lifestyle_for_report(user, days, bundle):
    """
    Same objects as lifestyle/recommendations/: LLM lifestyle from bundle when available,
    else rule-based. Used so PDF / doctor report includes actionable lifestyle guidance.
    """
    if bundle.get("status") == "success" and bundle.get("lifestyle"):
        return bundle["lifestyle"], True
    mood_ctx = _build_mood_context_for_lifestyle(user, days=days)
    mood_analysis_result = mood_ctx["mood_analysis_result"]
    stress_level = mood_ctx["stress_level"]
    cycle_phase_info = None
    try:
        profile = CycleProfile.objects.get(user=user)
        cycle_phase_info = get_cycle_status(
            profile.last_period_start_date,
            profile.average_cycle_length_days,
            profile.average_period_length_days,
        )
    except CycleProfile.DoesNotExist:
        pass
    return (
        generate_lifestyle_recommendations(
            mood_analysis_result, cycle_phase_info, stress_level
        ),
        False,
    )


def _merge_ai_bundle_into_report(report_data, user, days, bundle):
    """Attach LLM narrative + lifestyle block (for UI/PDF, doctor review)."""
    if bundle.get("status") == "success" and bundle.get("report_ai"):
        report_data["llm_insights"] = bundle["report_ai"]
    report_data["llm_generated"] = (
        bundle.get("status") == "success" and bundle.get("report_ai") is not None
    )
    lifestyle, lifestyle_llm = _lifestyle_for_report(user, days, bundle)
    report_data["lifestyle_recommendations"] = lifestyle
    report_data["lifestyle_llm_generated"] = lifestyle_llm


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def health_summary_report(request):
    """
    Phase 6: Generate Health Summary (AI Health Report).
    User clicks "Generate Health Summary" → backend compiles mood stats, cycle patterns,
    stress markers, lifestyle consistency; returns professional report, risk flags, suggestions, summary.
    Query params: days (default 30).
    """
    days = int(request.query_params.get("days", 30))
    user = request.user
    compiled = _build_health_summary_compiled_data(user, days=days)
    report_data = generate_health_summary_report(compiled)
    report_data["generated_at"] = timezone.now().isoformat()
    bundle = _get_llm_lifestyle_report_bundle(user, days=days, compiled=compiled)
    _merge_ai_bundle_into_report(report_data, user, days, bundle)
    return Response({
        "source": "ai_engine",
        "generated_by": "AI Health Report Generator",
        "message": (
            "Structured sections from compiled data; llm_insights = AI narrative; "
            "lifestyle_recommendations = same AI bundle as Lifestyle Intelligence when available "
            "(else rule-based), suitable for PDF / clinician review."
        ),
        "period_days": days,
        "report": report_data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def health_summary_export(request):
    """
    Phase 6: Export Health Summary (e.g. for PDF).
    Returns the same report as JSON with export_ready flag for frontend PDF generation (print-to-PDF or js PDF lib).
    Query params: days (default 30).
    """
    days = int(request.query_params.get("days", 30))
    user = request.user
    compiled = _build_health_summary_compiled_data(user, days=days)
    report_data = generate_health_summary_report(compiled)
    report_data["generated_at"] = timezone.now().isoformat()
    bundle = _get_llm_lifestyle_report_bundle(user, days=days, compiled=compiled)
    _merge_ai_bundle_into_report(report_data, user, days, bundle)
    return Response({
        "source": "ai_engine",
        "export_ready": True,
        "period_days": days,
        "report": report_data,
        "message": (
            "Use for PDF export. report.lifestyle_recommendations mirrors Lifestyle Intelligence "
            "(AI when llm bundle succeeds). Prefer compact 2-page layout on the client."
        ),
    })


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
# 🤖 NIVARA CHATBOT (Azure OpenAI – generic_chat)
# One user message → one backend request → one Azure API call (cost-optimised).
# Frontend sends history in body; we do not call the API multiple times per turn.
# =========================================================

def _chat_history_turns_from_db(session, max_turns=8):
    """Build history list for Azure from stored messages (last N complete turns)."""
    from .ai_engine.generic_chat import MAX_HISTORY_TURNS
    max_turns = min(max_turns, MAX_HISTORY_TURNS)
    msgs = list(ChatMessage.objects.filter(session=session).order_by("id"))
    msgs = msgs[-(max_turns * 2) :]
    turns = []
    i = 0
    while i < len(msgs) - 1:
        if msgs[i].role == "user" and msgs[i + 1].role == "assistant":
            turns.append({"human_msg": msgs[i].content, "ai_msg": msgs[i + 1].content})
            i += 2
        else:
            i += 1
    return turns


def _nivara_single_llm_turn(request, message: str):
    """
    Exactly ONE Azure OpenAI (GPT) API call per message (generic_chat.generate_chat_response).
    """
    try:
        from .ai_engine.generic_chat import generate_chat_response, MAX_HISTORY_TURNS
    except ModuleNotFoundError as e:
        if "openai" in str(e).lower():
            return Response(
                {
                    "error": "Missing dependency",
                    "detail": 'Install in your venv: pip install openai python-dotenv',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        raise

    message = (message or "").strip()
    if not message:
        return Response({"error": "Message required"}, status=status.HTTP_400_BAD_REQUEST)

    session_id = request.data.get("session_id")
    has_session_id = session_id is not None and str(session_id).strip() != ""

    if request.user.is_authenticated and not has_session_id:
        # New conversation: create session in this request (avoids extra POST /api/chat/sessions/)
        from .db_retry import sqlite_write

        def _create():
            return ChatSession.objects.create(user=request.user, title="")

        session = sqlite_write(_create)
        use_db_history = True
        history = []
    elif request.user.is_authenticated and has_session_id:
        try:
            sid = int(session_id)
        except (TypeError, ValueError):
            return Response({"error": "Invalid session_id"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session = ChatSession.objects.get(id=sid, user=request.user)
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
        use_db_history = True
        history = _chat_history_turns_from_db(session)
    else:
        session = None
        use_db_history = False
        history = request.data.get("history")
        if not isinstance(history, list):
            history = []
        history = [
            {"human_msg": str(t.get("human_msg", "")), "ai_msg": str(t.get("ai_msg", ""))}
            for t in history
            if isinstance(t, dict) and (t.get("human_msg") or t.get("ai_msg"))
        ]

    reply = generate_chat_response(history, message)
    from .chat_formatting import compact_assistant_reply
    reply = compact_assistant_reply(reply)

    if use_db_history and reply and not reply.startswith("[Error"):
        from .db_retry import sqlite_write

        def _save_chat_turn():
            ChatMessage.objects.create(session=session, role="user", content=message)
            ChatMessage.objects.create(session=session, role="assistant", content=reply)
            if not session.title:
                session.title = (message[:197] + "...") if len(message) > 200 else message
                session.save(update_fields=["title", "updated_at"])
            else:
                session.save(update_fields=["updated_at"])
            return _chat_history_turns_from_db(session)

        updated_history = sqlite_write(_save_chat_turn)
    else:
        updated_history = list(history)
        if reply and not reply.startswith("[Error"):
            updated_history.append({"human_msg": message, "ai_msg": reply})
            updated_history = updated_history[-MAX_HISTORY_TURNS:]

    out = {"reply": reply, "history": updated_history}
    if use_db_history:
        out["session_id"] = session.id
    return Response(out)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def chat_nivara(request):
    """
    Text chat: exactly ONE GPT call per request (lowest LLM cost).

    A) Logged-in + session_id: { "message", "session_id" }
    B) Guest: { "message", "history": [...] }
    """
    return _nivara_single_llm_turn(request, request.data.get("message") or "")


class ChatSessionsView(APIView):
    """
    GET: list past sessions (no Azure).
    POST: start new session (no Azure).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ChatSession.objects.filter(user=request.user)[:100]
        data = [
            {
                "id": s.id,
                "title": s.title or "New conversation",
                "updated_at": s.updated_at.isoformat(),
                "created_at": s.created_at.isoformat(),
            }
            for s in qs
        ]
        return Response({"count": len(data), "sessions": data})

    def post(self, request):
        from .db_retry import sqlite_write

        def _create():
            return ChatSession.objects.create(user=request.user, title="")

        s = sqlite_write(_create)
        return Response(
            {
                "session_id": s.id,
                "message": "New session started. POST to /api/chat/nivara/ with session_id and message.",
            },
            status=status.HTTP_201_CREATED,
        )


class ChatSessionDetailView(APIView):
    """Full conversation for one session (read-only). No Azure call."""
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            s = ChatSession.objects.get(id=session_id, user=request.user)
        except ChatSession.DoesNotExist:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
        msgs = ChatMessage.objects.filter(session=s).order_by("id")
        messages = [
            {
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ]
        return Response(
            {
                "session_id": s.id,
                "title": s.title or "Conversation",
                "updated_at": s.updated_at.isoformat(),
                "messages": messages,
            }
        )


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
        
        # Generate insights (rule-based fallback / extra context)
        insights = generate_personalized_insights(cycle_status, mood_data, checkin_data)

        days = int(request.query_params.get("mood_window_days", 30))
        period_logs = list(
            PeriodLog.objects.filter(user=request.user).values(
                "period_start_date",
                "cycle_length_from_previous",
                "actual_period_length",
            )
        )
        regularity = (
            detect_irregularity(period_logs, profile.average_cycle_length_days)
            if len(period_logs) >= 2
            else {"has_data": False, "message": "Need at least 2 period records for irregularity analysis"}
        )

        wellness_payload = _build_wellness_llm_payload(request.user, days=days)
        llm_result = _get_wellness_llm_analysis(
            request.user, days=days, payload=wellness_payload
        )
        llm_block = _shape_cycle_llm_insights(llm_result, regularity)
        prediction = {
            "predicted_next_period": cycle_status.get("predicted_next_period"),
            "days_until_next_period": cycle_status.get("days_until_next_period"),
            "countdown_message": cycle_status.get("countdown_message"),
        }

        return Response({
            "cycle_status": cycle_status,
            "insights": insights,
            "regularity_analysis": regularity,
            "prediction": prediction,
            "llm": {
                "generated": llm_result.get("status") == "success",
                "personalized_insights": llm_block.get("personalized_insights", ""),
                "mood_cycle_connection": llm_block.get("mood_cycle_connection", ""),
                "cycle_regularity_narrative": llm_block.get("cycle_regularity_narrative", ""),
                "alerts": llm_block.get("alerts", []),
                "phase_tips": llm_block.get("phase_tips", {}),
                "error": llm_block.get("error"),
            },
            "mood_window_days": days,
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


# =========================================================
# 🏥 PHASE 7: DOCTOR CONSULTATION LAYER
# AI Insight → Human Expertise: Book doctor, share report, virtual consultation
# =========================================================

class HospitalListView(APIView):
    """List all active hospitals (for dropdown / browse)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        hospitals = Hospital.objects.filter(is_active=True).order_by('city', 'name')
        serializer = HospitalSerializer(hospitals, many=True)
        return Response({"count": hospitals.count(), "hospitals": serializer.data})


class DoctorListView(APIView):
    """List doctors; optional filters: hospital_id, specialization."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Doctor.objects.filter(is_active=True).select_related('hospital').order_by('name')
        hospital_id = request.query_params.get('hospital_id')
        specialization = request.query_params.get('specialization')
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        if specialization:
            qs = qs.filter(specialization=specialization)
        serializer = DoctorListSerializer(qs, many=True)
        return Response({"count": qs.count(), "doctors": serializer.data})


class DoctorDetailView(APIView):
    """Get single doctor with hospital details."""
    permission_classes = [IsAuthenticated]

    def get(self, request, doctor_id):
        try:
            doctor = Doctor.objects.select_related('hospital').get(id=doctor_id, is_active=True)
            serializer = DoctorSerializer(doctor)
            return Response(serializer.data)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def doctor_consultation_options(request):
    """Payment methods and consultation types for frontend dropdowns."""
    return Response({
        "payment_methods": [
            {"value": "upi", "label": "UPI"},
            {"value": "debit_card", "label": "Debit Card"},
            {"value": "credit_card", "label": "Credit Card"},
            {"value": "net_banking", "label": "Net Banking"},
            {"value": "wallet", "label": "Wallet"},
        ],
        "consultation_types": [
            {"value": "virtual", "label": "Virtual Consultation"},
            {"value": "in_person", "label": "In-Person Visit"},
        ],
        "doctor_specializations": [
            {"value": "gynecology", "label": "Gynecology"},
            {"value": "obstetrics", "label": "Obstetrics"},
            {"value": "reproductive_endocrinology", "label": "Reproductive Endocrinology"},
            {"value": "womens_health", "label": "Women's Health & Wellness"},
            {"value": "fertility", "label": "Fertility Specialist"},
            {"value": "pcos", "label": "PCOS & Hormonal Health"},
            {"value": "menopause", "label": "Menopause Care"},
        ],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_for_booking(request):
    """Get current user's AI health report for sharing with doctor (used when share_report=true)."""
    days = int(request.query_params.get("days", 30))
    user = request.user
    compiled = _build_health_summary_compiled_data(user, days=days)
    report_data = generate_health_summary_report(compiled)
    report_data["generated_at"] = timezone.now().isoformat()
    bundle = _get_llm_lifestyle_report_bundle(user, days=days, compiled=compiled)
    _merge_ai_bundle_into_report(report_data, user, days, bundle)
    return Response({
        "report": report_data,
        "period_days": days,
        "message": "Use this report when booking to share with your doctor.",
    })


class DoctorBookingCreateView(APIView):
    """Create a doctor consultation booking. If report_shared=True, attach current AI report snapshot."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DoctorConsultationBookingCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        doctor_id = serializer.validated_data["doctor"].id
        try:
            doctor = Doctor.objects.get(id=doctor_id, is_active=True)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

        report_shared = serializer.validated_data.get("report_shared", False)
        report_snapshot = None
        if report_shared:
            compiled = _build_health_summary_compiled_data(request.user, days=30)
            report_snapshot = generate_health_summary_report(compiled)
            report_snapshot["generated_at"] = timezone.now().isoformat()
            bundle = _get_llm_lifestyle_report_bundle(
                request.user, days=30, compiled=compiled
            )
            _merge_ai_bundle_into_report(report_snapshot, request.user, 30, bundle)

        booking = DoctorConsultationBooking.objects.create(
            user=request.user,
            doctor=doctor,
            scheduled_at=serializer.validated_data["scheduled_at"],
            consultation_type=serializer.validated_data.get("consultation_type", "virtual"),
            report_shared=report_shared,
            report_snapshot=report_snapshot,
            notes=serializer.validated_data.get("notes", ""),
            status="payment_pending",
        )
        # Create pending payment record; user selects method in payment/initiate
        Payment.objects.create(
            booking=booking,
            amount=doctor.consultation_fee,
            currency="INR",
            payment_method="pending",
            payment_status="pending",
        )
        booking_serializer = DoctorConsultationBookingSerializer(booking)
        return Response({
            "message": "Booking created. Complete payment to confirm.",
            "booking": booking_serializer.data,
        }, status=status.HTTP_201_CREATED)


class DoctorBookingListView(APIView):
    """List current user's doctor consultation bookings."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = DoctorConsultationBooking.objects.filter(user=request.user).select_related(
            "doctor", "doctor__hospital"
        ).prefetch_related("payment").order_by("-scheduled_at")
        serializer = DoctorConsultationBookingSerializer(bookings, many=True)
        return Response({"count": bookings.count(), "bookings": serializer.data})


class DoctorBookingDetailView(APIView):
    """Get one booking by id (for payment page)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        try:
            booking = DoctorConsultationBooking.objects.select_related(
                "doctor", "doctor__hospital"
            ).get(id=booking_id, user=request.user)
            serializer = DoctorConsultationBookingSerializer(booking)
            return Response(serializer.data)
        except DoctorConsultationBooking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)


class PaymentInitiateView(APIView):
    """Initiate payment for a booking (dummy: just records method and returns order_id)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        try:
            booking = DoctorConsultationBooking.objects.get(id=booking_id, user=request.user)
        except DoctorConsultationBooking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

        if booking.status not in ("pending", "payment_pending"):
            return Response(
                {"error": "Booking is not in payment pending state."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = PaymentInitiateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        payment_method = ser.validated_data["payment_method"]
        payment_metadata = {}
        if ser.validated_data.get("upi_id"):
            payment_metadata["upi_id"] = ser.validated_data["upi_id"]
        if ser.validated_data.get("card_last4"):
            payment_metadata["card_last4"] = ser.validated_data["card_last4"]
        if ser.validated_data.get("bank_code"):
            payment_metadata["bank_code"] = ser.validated_data["bank_code"]
        if ser.validated_data.get("wallet_type"):
            payment_metadata["wallet_type"] = ser.validated_data["wallet_type"]

        try:
            payment = booking.payment
        except Payment.DoesNotExist:
            payment = None
        if not payment:
            payment = Payment.objects.create(
                booking=booking,
                amount=booking.doctor.consultation_fee,
                currency="INR",
                payment_method=payment_method,
                payment_status="pending",
                payment_metadata=payment_metadata,
            )
        else:
            payment.payment_method = payment_method
            payment.payment_metadata = {**payment.payment_metadata, **payment_metadata}
            payment.save(update_fields=["payment_method", "payment_metadata"])

        # Dummy transaction id for frontend to show and send back on confirm
        import uuid
        order_id = f"NIVARA_{booking.id}_{uuid.uuid4().hex[:8].upper()}"
        return Response({
            "message": "Payment initiated (dummy gateway). Use confirm endpoint with transaction_id.",
            "payment_id": payment.id,
            "order_id": order_id,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method,
        })


class PaymentConfirmView(APIView):
    """Confirm payment (dummy: marks payment completed and booking confirmed)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        try:
            booking = DoctorConsultationBooking.objects.get(id=booking_id, user=request.user)
        except DoctorConsultationBooking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            payment = booking.payment
        except Payment.DoesNotExist:
            return Response({"error": "No payment record for this booking."}, status=status.HTTP_400_BAD_REQUEST)

        if payment.payment_status == "completed":
            return Response({
                "message": "Payment already completed.",
                "booking": DoctorConsultationBookingSerializer(booking).data,
            })

        ser = PaymentConfirmSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        payment.transaction_id = ser.validated_data["transaction_id"]
        payment.payment_status = "completed"
        payment.paid_at = timezone.now()
        meta = dict(payment.payment_metadata or {})
        if ser.validated_data.get("upi_id"):
            meta["upi_id"] = ser.validated_data["upi_id"]
        if ser.validated_data.get("card_last4"):
            meta["card_last4"] = ser.validated_data["card_last4"]
        if ser.validated_data.get("bank_name"):
            meta["bank_name"] = ser.validated_data["bank_name"]
        payment.payment_metadata = meta
        payment.save(update_fields=["transaction_id", "payment_status", "paid_at", "payment_metadata"])

        booking.status = "confirmed"
        booking.save(update_fields=["status"])

        return Response({
            "message": "Payment successful. Your consultation is confirmed.",
            "booking": DoctorConsultationBookingSerializer(booking).data,
            "payment": PaymentSerializer(payment).data,
        })