from django.db import models
from django.contrib.auth.models import User


# ─── Financial Profile ────────────────────────────────────────────────────────
class FinancialProfile(models.Model):
    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profiles')
    name            = models.CharField(max_length=100)          # e.g. Personal, Business
    monthly_salary  = models.FloatField(default=0)
    additional_income = models.FloatField(default=0)
    current_savings = models.FloatField(default=0)
    monthly_budget  = models.FloatField(default=0)
    savings_goal    = models.FloatField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → {self.name}"


# ─── Expense (profile-scoped) ─────────────────────────────────────────────────
CATEGORY_CHOICES = [
    ('Food',     'Food'),
    ('Rent',     'Rent'),
    ('Travel',   'Travel'),
    ('Shopping', 'Shopping'),
    ('Bills',    'Bills'),
    ('Other',    'Other'),
]

class Expense(models.Model):
    profile  = models.ForeignKey(FinancialProfile, on_delete=models.CASCADE, related_name='expenses')
    amount   = models.FloatField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    date     = models.DateField()
    notes    = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.name} | {self.category} ₹{self.amount} on {self.date}"


# ─── Stress Prediction Log ────────────────────────────────────────────────────
class StressRecord(models.Model):
    monthly_income  = models.FloatField()
    monthly_expense = models.FloatField()
    stress_level    = models.CharField(max_length=20)
    confidence      = models.FloatField(default=0)
    expense_ratio   = models.FloatField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.stress_level} - {self.created_at}"