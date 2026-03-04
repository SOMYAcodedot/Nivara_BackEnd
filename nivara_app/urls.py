from django.urls import path
from .views import (
    SignupView,
    LoginView,
    LogoutView,
    log_mood,
    mood_history,
    run_mood_analysis,
    # Phase 2: Mood Analytics APIs
    mood_trend_data,
    emotion_distribution,
    stress_pattern_data,
    mood_analytics_summary,
    mood_history_detailed,
    log_cycle,              # ✅ corrected
    predict_cycle_view,
    lifestyle_plan,
    generate_report,
    chat_with_ai,
    DashboardView,
    # Phase 3: Cycle Intelligence APIs
    CycleProfileView,
    PeriodLogView,
    PeriodLogDetailView,
    DailyCheckinView,
    TodayCheckinView,
    CycleStatusView,
    CycleDashboardView,
    CycleInsightsView,
    CycleIrregularityView,
    CycleCalendarView,
    OnboardingStatusView,
    cycle_options,
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
    # 📊 PHASE 2: MOOD ANALYTICS (Graphical Data)
    # ===============================
    path("mood/trend/", mood_trend_data, name="mood_trend"),
    path("mood/emotions/", emotion_distribution, name="emotion_distribution"),
    path("mood/stress/", stress_pattern_data, name="stress_pattern"),
    path("mood/summary/", mood_analytics_summary, name="mood_summary"),
    path("mood/history/detailed/", mood_history_detailed, name="mood_history_detailed"),

    # ===============================
    # 🤖 AI CHATBOT
    # ===============================
    path("chat/", chat_with_ai, name="chat_with_ai"),

    # ===============================
    # 🌸 CYCLE INTELLIGENCE (Legacy)
    # ===============================
    path("cycle/log/", log_cycle, name="log_cycle"),
    path("cycle/predict/", predict_cycle_view, name="cycle_prediction"),

    # ===============================
    # 🌸 PHASE 3: CYCLE INTELLIGENCE LAYER
    # ===============================
    
    # Cycle Profile (Onboarding)
    path("cycle/profile/", CycleProfileView.as_view(), name="cycle_profile"),
    path("cycle/onboarding-status/", OnboardingStatusView.as_view(), name="onboarding_status"),
    path("cycle/options/", cycle_options, name="cycle_options"),
    
    # Period Logging
    path("cycle/period/", PeriodLogView.as_view(), name="period_log"),
    path("cycle/period/<int:log_id>/", PeriodLogDetailView.as_view(), name="period_log_detail"),
    
    # Daily Checkin
    path("cycle/checkin/", DailyCheckinView.as_view(), name="daily_checkin"),
    path("cycle/checkin/today/", TodayCheckinView.as_view(), name="today_checkin"),
    
    # Cycle Status & Dashboard
    path("cycle/status/", CycleStatusView.as_view(), name="cycle_status"),
    path("cycle/dashboard/", CycleDashboardView.as_view(), name="cycle_dashboard"),
    
    # Cycle Insights & Analysis
    path("cycle/insights/", CycleInsightsView.as_view(), name="cycle_insights"),
    path("cycle/irregularity/", CycleIrregularityView.as_view(), name="cycle_irregularity"),
    path("cycle/calendar/", CycleCalendarView.as_view(), name="cycle_calendar"),

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