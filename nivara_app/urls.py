
# from django.urls import path
# from .views import (
#     SignupView, LoginView, LogoutView, log_mood, get_mood_history,
#     chat_with_ai, DashboardView
# )
# from rest_framework_simplejwt.views import TokenRefreshView

# urlpatterns = [
#     # ✅ Authentication Endpoints
#     path("signup/", SignupView.as_view(), name="signup"),
#     path("login/", LoginView.as_view(), name="login"),
#     path("logout/", LogoutView.as_view(), name="logout"),
#     path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

#     # ✅ Mood Tracking Endpoints
#     path("mood/log/", log_mood, name="log-mood"),
#     path("mood/history/", get_mood_history, name="mood-history"),

#     # ✅ AI Chatbot Endpoint
#     path("chat/", chat_with_ai, name="chat_with_ai"),

#     # ✅ Dashboard Endpoint (Public Access)
#     path("dashboard/", DashboardView.as_view(), name="dashboard"),
# ]






# from django.urls import path
# from .views import SignupView
# from rest_framework_simplejwt.views import (
#     TokenObtainPairView,
#     TokenRefreshView,
# )

# urlpatterns = [
#     path('signup/', SignupView.as_view(), name='signup'),
#     path('login/', TokenObtainPairView.as_view(), name='login'),
#     path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
# ]








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
    path("lifestyle/plan/", predict_cycle_view, name="lifestyle_plan"),

    # ===============================
    # 📊 HEALTH REPORT
    # ===============================
    path("report/generate/", predict_cycle_view, name="health_report"),

    # ===============================
    # 🏠 DASHBOARD
    # ===============================
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]