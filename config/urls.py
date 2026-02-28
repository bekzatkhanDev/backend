from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('taxi.urls')),
]