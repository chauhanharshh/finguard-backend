from django.contrib import admin
from .models import FinancialProfile, Expense, StressRecord

admin.site.register(FinancialProfile)
admin.site.register(Expense)
admin.site.register(StressRecord)
