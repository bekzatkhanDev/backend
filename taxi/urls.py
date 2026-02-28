from django.urls import path
from . import views

app_name = 'taxi_api'

urlpatterns = [
    # === 1. Аутентификация ===
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/refresh/', views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # === 2. Пользователи и профили ===
    path('users/me/', views.CurrentUserProfileView.as_view(), name='current-user-profile'),
    path('users/<int:id>/', views.AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('users/', views.AdminUserListView.as_view(), name='admin-user-list'),
    path('users/<int:id>/roles/', views.AdminUserRoleUpdateView.as_view(), name='admin-user-role-update'),

    # === Профиль водителя ===
    path('drivers/profile/', views.DriverProfileCreateView.as_view(), name='driver-profile-create'),
    path('drivers/profile/me/', views.DriverProfileMeView.as_view(), name='driver-profile-me'),

    # === 3. Автомобили водителя ===
    path('drivers/cars/', views.MyCarsListView.as_view(), name='my-cars-list'),
    path('drivers/cars/<int:id>/', views.MyCarDetailView.as_view(), name='my-car-detail'),
    path('cars/<int:id>/', views.AdminCarDetailView.as_view(), name='admin-car-detail'),

    # === 4. Справочники ===
    path('car-brands/', views.CarBrandListView.as_view(), name='car-brand-list'),
    path('car-types/', views.CarTypeListView.as_view(), name='car-type-list'),
    path('tariffs/', views.TariffListView.as_view(), name='tariff-list'),
    path('tariffs/<int:id>/', views.TariffDetailView.as_view(), name='tariff-detail'),
    path('tariffs/estimates/', views.BulkTariffEstimateView.as_view(), name='bulk-tariff-estimates'),

    # === 5. Геолокация ===
    path('locations/', views.UpdateLocationView.as_view(), name='update-location'),
    path('locations/me/', views.MyLocationView.as_view(), name='my-location'),
    path('locations/nearby/', views.NearbyCarsView.as_view(), name='nearby-cars'),

    # === 6. Расчёт стоимости ===
    path('trips/estimate/', views.TripEstimateView.as_view(), name='trip-estimate'),

    # === 7. Поездки ===
    path('trips/', views.TripCreateView.as_view(), name='trip-create'),
    path('trips/active/', views.ActiveTripView.as_view(), name='active-trip'),
    path('trips/<uuid:id>/', views.TripDetailView.as_view(), name='trip-detail'),
    path('trips/history/', views.TripHistoryView.as_view(), name='trip-history'),
    path('trips/<uuid:id>/cancel/', views.CancelTripView.as_view(), name='cancel-trip'),

    # === 8. Отзывы ===
    path('trips/<uuid:id>/review/', views.CreateReviewView.as_view(), name='review-create'),
    path('reviews/user/<int:id>/', views.UserReviewsView.as_view(), name='user-reviews'),

    # === 9. Оплата ===
    path('payments/', views.CreatePaymentView.as_view(), name='payment-create'),
    path('payments/<int:id>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    path('payments/trip/<uuid:trip_id>/', views.PaymentByTripView.as_view(), name='payment-by-trip'),
]
