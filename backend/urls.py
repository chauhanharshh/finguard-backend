from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # 🔥 YOUR APP
    path('api/', include('api.urls')),
]