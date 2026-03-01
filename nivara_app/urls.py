from django.urls import path
from .views import (
    SignupView,
    LoginView,
    LogoutView,
    log_mood,
    mood_history,
    run_mood_analysis,
    log_cycle,              # ✅ corrected
    predict_cycle_view,
    lifestyle_plan,
    generate_report,
    chat_with_ai,
    DashboardView
)

from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [

    # ===============================
    # 🔐 AUTHENTICATION
    # ===============================
    path("auth/signup/", SignupView.as_view(), name="signup"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # ===============================
    # 🧠 MOOD MODULE
    # ===============================
    path("mood/log/", log_mood, name="log_mood"),
    path("mood/history/", mood_history, name="mood_history"),
    path("mood/analysis/", run_mood_analysis, name="mood_analysis"),

    # ===============================
    # 🤖 AI CHATBOT
    # ===============================
    path("chat/", chat_with_ai, name="chat_with_ai"),

    # ===============================
    # 🌸 CYCLE INTELLIGENCE
    # ===============================
    path("cycle/log/", log_cycle, name="log_cycle"),
    path("cycle/predict/", predict_cycle_view, name="cycle_prediction"),

    # ===============================
    # 🥗 LIFESTYLE AI
    # ===============================
    path("lifestyle/plan/", lifestyle_plan, name="lifestyle_plan"),

    # ===============================
    # 📊 HEALTH REPORT
    # ===============================
    path("report/generate/", generate_report, name="health_report"),

    # ===============================
    # 🏠 DASHBOARD
    # ===============================
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]