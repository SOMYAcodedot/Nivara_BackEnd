from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, timedelta

from .models import MoodEntry, CycleEntry
from .serializers import MoodEntrySerializer, CycleEntrySerializer

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