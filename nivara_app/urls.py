from django.urls import path
from .views import (
    SignupView,
    LoginView,
    LogoutView,
    UserProfileView,
    ProfileStatusView,
    lifestyle_options,
    log_mood,
    mood_history,
    run_mood_analysis,
    # Phase 2: Mood Analytics APIs
    mood_trend_data,
    emotion_distribution,
    stress_pattern_data,
    mood_analytics_summary,
    mood_history_detailed,
    mood_insights_ai,
    log_cycle,              # ✅ corrected
    predict_cycle_view,
    lifestyle_plan,
    lifestyle_recommendations,
    lifestyle_recommendations_context,
    generate_report,
    health_summary_report,
    health_summary_export,
    chat_with_ai,
    chat_nivara,
    ChatSessionsView,
    ChatSessionDetailView,
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
    # Phase 7: Doctor Consultation
    HospitalListView,
    DoctorListView,
    DoctorDetailView,
    doctor_consultation_options,
    report_for_booking,
    DoctorBookingCreateView,
    DoctorBookingListView,
    DoctorBookingDetailView,
    PaymentInitiateView,
    PaymentConfirmView,
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
    # 👤 USER PROFILE (STEP 1 - One-Time Setup)
    # ===============================
    path("user/profile/", UserProfileView.as_view(), name="user_profile"),
    path("user/profile-status/", ProfileStatusView.as_view(), name="profile_status"),
    path("user/lifestyle-options/", lifestyle_options, name="lifestyle_options"),

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
    path("mood/insights-ai/", mood_insights_ai, name="mood_insights_ai"),

    # ===============================
    # 🤖 AI CHATBOT
    # ===============================
    path("chat/", chat_with_ai, name="chat_with_ai"),
    path("chat/nivara/", chat_nivara, name="chat_nivara"),
    path("chat/sessions/", ChatSessionsView.as_view(), name="chat_sessions"),
    path("chat/sessions/<int:session_id>/", ChatSessionDetailView.as_view(), name="chat_session_detail"),

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
    # 🌿 PHASE 4: LIFESTYLE INTELLIGENCE (Recommendation Engine)
    # ===============================
    path("lifestyle/recommendations/", lifestyle_recommendations, name="lifestyle_recommendations"),
    path("lifestyle/recommendations/context/", lifestyle_recommendations_context, name="lifestyle_recommendations_context"),

    # ===============================
    # 📊 HEALTH REPORT
    # ===============================
    path("report/generate/", generate_report, name="health_report"),

    # ===============================
    # 🌸 PHASE 6: AI HEALTH REPORT (Generate Health Summary)
    # ===============================
    path("report/summary/", health_summary_report, name="health_summary_report"),
    path("report/summary/export/", health_summary_export, name="health_summary_export"),

    # ===============================
    # 🏠 DASHBOARD
    # ===============================
    path("dashboard/", DashboardView.as_view(), name="dashboard"),

    # ===============================
    # 🏥 PHASE 7: DOCTOR CONSULTATION
    # ===============================
    path("doctor/hospitals/", HospitalListView.as_view(), name="doctor_hospitals"),
    path("doctor/doctors/", DoctorListView.as_view(), name="doctor_list"),
    path("doctor/doctors/<int:doctor_id>/", DoctorDetailView.as_view(), name="doctor_detail"),
    path("doctor/options/", doctor_consultation_options, name="doctor_consultation_options"),
    path("doctor/report-for-booking/", report_for_booking, name="report_for_booking"),
    path("doctor/booking/", DoctorBookingCreateView.as_view(), name="doctor_booking_create"),
    path("doctor/bookings/", DoctorBookingListView.as_view(), name="doctor_booking_list"),
    path("doctor/booking/<int:booking_id>/", DoctorBookingDetailView.as_view(), name="doctor_booking_detail"),
    path("doctor/booking/<int:booking_id>/payment/initiate/", PaymentInitiateView.as_view(), name="payment_initiate"),
    path("doctor/booking/<int:booking_id>/payment/confirm/", PaymentConfirmView.as_view(), name="payment_confirm"),
]