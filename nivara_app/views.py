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
from datetime import datetime, timedelta

from .models import MoodEntry, CycleEntry
from .serializers import MoodEntrySerializer, MoodEntryDetailSerializer, CycleEntrySerializer

User = get_user_model()

# AI ENGINE IMPORTS
from .ai_engine.mood_analysis import analyze_mood_entries
from .ai_engine.chatbot_engine import chatbot_response
from .ai_engine.cycle_logic import predict_cycle
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