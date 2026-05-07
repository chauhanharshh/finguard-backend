from django.urls import path
from .views import (
    register, login,
    profiles, profile_detail,
    profile_expenses, profile_expense_detail,
    profile_dashboard,
    dashboard, expenses, expense_detail,
    analysis, alerts, recommendations, forecast, loan,
    stress_prediction,
)

urlpatterns = [
    # 🔐 AUTH
    path('register/',   register),
    path('login/',      login),

    # 👤 FINANCIAL PROFILES
    path('profiles/',          profiles),           # GET (list) | POST (create)
    path('profiles/<int:pk>/', profile_detail),     # GET | PUT | DELETE

    # 💸 PROFILE-SCOPED EXPENSES
    path('profiles/<int:pk>/expenses/',                  profile_expenses),
    path('profiles/<int:pk>/expenses/<int:eid>/',        profile_expense_detail),

    # 📊 PROFILE DASHBOARD
    path('profiles/<int:pk>/dashboard/',                 profile_dashboard),

    # 🧠 STRESS PREDICTION (global)
    path('predict-stress/', stress_prediction),

    # ─── Legacy / stub endpoints (kept so old imports don't crash) ───
    path('dashboard/',          dashboard),
    path('expenses/',           expenses),
    path('expenses/<int:pk>/',  expense_detail),
    path('analysis/',           analysis),
    path('alerts/',             alerts),
    path('recommendations/',    recommendations),
    path('forecast/',           forecast),
    path('loan/',               loan),
]