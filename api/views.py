from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import FinancialProfile, Expense, StressRecord
from .ml_model import predict_stress
from collections import defaultdict
import datetime


# ─── Auth helpers ──────────────────────────────────────────────────────────────
def get_user(request):
    """Return User from 'Authorization: Token <key>' header, or None."""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Token '):
        return None
    key = auth.split(' ', 1)[1]
    try:
        return Token.objects.get(key=key).user
    except Token.DoesNotExist:
        return None

def require_auth(request):
    user = get_user(request)
    if not user:
        return None, Response({'error': 'Unauthorized'}, status=401)
    return user, None

def require_profile(request, pk):
    user, err = require_auth(request)
    if err:
        return None, None, err
    try:
        profile = FinancialProfile.objects.get(pk=pk, user=user)
    except FinancialProfile.DoesNotExist:
        return user, None, Response({'error': 'Profile not found'}, status=404)
    return user, profile, None


# ─── REGISTER ─────────────────────────────────────────────────────────────────
@api_view(['POST'])
def register(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    if not username or not password:
        return Response({'error': 'Missing fields'}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({'error': 'User already exists'}, status=400)
    user = User.objects.create_user(username=username, password=password)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'message': 'User created', 'token': token.key}, status=201)


# ─── LOGIN ────────────────────────────────────────────────────────────────────
@api_view(['POST'])
def login(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    user = User.objects.filter(username=username).first()
    if user and user.check_password(password):
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'message': 'Login successful', 'token': token.key})
    return Response({'error': 'Invalid credentials'}, status=401)


# ─── PROFILES ────────────────────────────────────────────────────────────────
def profile_data(p):
    return {
        'id': p.id,
        'name': p.name,
        'monthly_salary': p.monthly_salary,
        'additional_income': p.additional_income,
        'current_savings': p.current_savings,
        'monthly_budget': p.monthly_budget,
        'savings_goal': p.savings_goal,
        'created_at': str(p.created_at.date()),
    }

@api_view(['GET', 'POST'])
def profiles(request):
    user, err = require_auth(request)
    if err: return err

    if request.method == 'GET':
        return Response([profile_data(p) for p in FinancialProfile.objects.filter(user=user)])

    # POST — create
    p = FinancialProfile.objects.create(
        user=user,
        name=request.data.get('name', 'My Profile'),
        monthly_salary=request.data.get('monthly_salary', 0),
        additional_income=request.data.get('additional_income', 0),
        current_savings=request.data.get('current_savings', 0),
        monthly_budget=request.data.get('monthly_budget', 0),
        savings_goal=request.data.get('savings_goal', 0),
    )
    return Response(profile_data(p), status=201)


@api_view(['GET', 'PUT', 'DELETE'])
def profile_detail(request, pk):
    user, profile, err = require_profile(request, pk)
    if err: return err

    if request.method == 'GET':
        return Response(profile_data(profile))

    if request.method == 'PUT':
        for field in ['name', 'monthly_salary', 'additional_income', 'current_savings', 'monthly_budget', 'savings_goal']:
            if field in request.data:
                setattr(profile, field, request.data[field])
        profile.save()
        return Response(profile_data(profile))

    # DELETE — cascade removes expenses too
    profile.delete()
    return Response({'message': 'Profile deleted'}, status=204)


# ─── PROFILE EXPENSES ─────────────────────────────────────────────────────────
def expense_data(e):
    return {'id': e.id, 'amount': e.amount, 'category': e.category,
            'date': str(e.date), 'notes': e.notes}

@api_view(['GET', 'POST'])
def profile_expenses(request, pk):
    user, profile, err = require_profile(request, pk)
    if err: return err

    if request.method == 'GET':
        qs = profile.expenses.all().order_by('-date', '-created_at')
        return Response([expense_data(e) for e in qs])

    # POST
    try:
        e = Expense.objects.create(
            profile=profile,
            amount=float(request.data.get('amount', 0)),
            category=request.data.get('category', 'Other'),
            date=request.data.get('date'),
            notes=request.data.get('notes', ''),
        )
        return Response(expense_data(e), status=201)
    except Exception as ex:
        return Response({'error': str(ex)}, status=400)


@api_view(['PUT', 'DELETE'])
def profile_expense_detail(request, pk, eid):
    user, profile, err = require_profile(request, pk)
    if err: return err
    try:
        e = Expense.objects.get(pk=eid, profile=profile)
    except Expense.DoesNotExist:
        return Response({'error': 'Expense not found'}, status=404)

    if request.method == 'PUT':
        e.amount   = float(request.data.get('amount',   e.amount))
        e.category = request.data.get('category', e.category)
        e.date     = request.data.get('date',     e.date)
        e.notes    = request.data.get('notes',    e.notes)
        e.save()
        return Response(expense_data(e))

    e.delete()
    return Response({'message': 'Deleted'}, status=204)


# ─── PROFILE DASHBOARD ────────────────────────────────────────────────────────
@api_view(['GET'])
def profile_dashboard(request, pk):
    user, profile, err = require_profile(request, pk)
    if err: return err

    expenses = list(profile.expenses.all().order_by('-date', '-created_at'))
    total_income = profile.monthly_salary + profile.additional_income

    # This month
    today = datetime.date.today()
    this_month = [e for e in expenses if e.date.year == today.year and e.date.month == today.month]
    total_expenses = sum(e.amount for e in this_month)
    expense_ratio = round((total_expenses / (total_income or 1)) * 100, 1)

    # Risk score
    ratio = total_expenses / (total_income or 1)
    if ratio < 0.4:   risk, confidence = 'Low',    round(95 - ratio / 0.4 * 45, 1)
    elif ratio < 0.75: risk, confidence = 'Medium', round(60 + abs((ratio - 0.4) / (0.75 - 0.4) - 0.5) * 40, 1)
    else:              risk, confidence = 'High',   round(min(95, 55 + (ratio - 0.75) * 80), 1)

    # Budget
    budget_remaining = round(profile.monthly_budget - total_expenses, 2) if profile.monthly_budget else None

    # Last 7 days trend
    trend_raw = defaultdict(float)
    for e in expenses:
        if e.date >= today - datetime.timedelta(days=6):
            trend_raw[str(e.date)] += e.amount
    trend = [{'date': d, 'amount': round(v, 2)} for d, v in sorted(trend_raw.items())]

    # Category breakdown
    cat_raw = defaultdict(float)
    for e in this_month: cat_raw[e.category] += e.amount
    total_cat = sum(cat_raw.values()) or 1
    category_breakdown = [{'name': k, 'value': round(v, 2), 'pct': round(v / total_cat * 100, 1)}
                          for k, v in cat_raw.items()]

    # Recent 5
    recent = [expense_data(e) for e in expenses[:5]]

    return Response({
        'profile': profile_data(profile),
        'total_income': total_income,
        'total_expenses': round(total_expenses, 2),
        'expense_ratio': expense_ratio,
        'risk_score': risk,
        'confidence': confidence,
        'budget_remaining': budget_remaining,
        'savings': profile.current_savings,
        'savings_goal': profile.savings_goal,
        'trend': trend,
        'category_breakdown': category_breakdown,
        'recent_transactions': recent,
    })


# ─── STRESS PREDICTION (global, not profile-scoped) ───────────────────────────
@api_view(['POST'])
def stress_prediction(request):
    try:
        income  = float(request.data.get('monthly_income', 1) or 1)
        expense = float(request.data.get('monthly_expense_total', 0) or 0)
        if income <= 0: income = 1
        ratio = expense / income

        if ratio < 0.4:
            confidence, result = 95 - (ratio / 0.4) * 45, 'Low'
        elif ratio < 0.75:
            mid = (ratio - 0.4) / (0.75 - 0.4)
            confidence, result = 60 + abs(mid - 0.5) * 40, 'Medium'
        else:
            confidence, result = min(95, 55 + (ratio - 0.75) * 80), 'High'

        StressRecord.objects.create(
            monthly_income=income, monthly_expense=expense,
            stress_level=result, confidence=round(confidence, 1),
            expense_ratio=round(ratio, 4)
        )
        return Response({'status': 'success', 'stress_level': result,
                         'confidence': round(confidence, 1),
                         'expense_ratio': round(ratio * 100, 1)})
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=500)


# ─── LEGACY GLOBAL DASHBOARD (kept for backward compat) ───────────────────────
@api_view(['GET'])
def dashboard(request):
    latest = StressRecord.objects.order_by('-created_at').first()
    risk       = latest.stress_level   if latest else 'Low'
    confidence = latest.confidence     if latest else 0
    expense_ratio = latest.expense_ratio if latest else 0
    records = StressRecord.objects.order_by('-created_at')[:7]
    trend = [{'stress_level': r.stress_level, 'confidence': round(r.confidence, 1),
               'expense_ratio': round(r.expense_ratio * 100, 1),
               'created_at': r.created_at.strftime('%H:%M')}
              for r in reversed(list(records))]
    return Response({'risk_score': risk, 'confidence': round(confidence, 1),
                     'expense_ratio': round(expense_ratio * 100, 1), 'trend': trend})


# ─── OTHER STUBS ──────────────────────────────────────────────────────────────
@api_view(['GET'])
def expenses(request):
    user, err = require_auth(request)
    if err: return err
    return Response([])

@api_view(['PUT', 'DELETE'])
def expense_detail(request, pk):
    return Response({'error': 'Use profile-scoped endpoint'}, status=400)

@api_view(['GET'])
def analysis(request):
    return Response({'message': 'Use /api/profiles/<id>/dashboard/ for analytics'})

@api_view(['GET'])
def alerts(request):
    return Response([])

@api_view(['GET'])
def recommendations(request):
    return Response([])

@api_view(['GET'])
def forecast(request):
    return Response({})

@api_view(['GET'])
def loan(request):
    return Response({})