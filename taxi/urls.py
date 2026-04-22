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
    path('drivers/me/online-status/', views.DriverOnlineStatusView.as_view(), name='driver-online-status'),
    path('drivers/me/dashboard/', views.DriverDashboardView.as_view(), name='driver-dashboard'),
    path('drivers/me/earnings/', views.DriverEarningsView.as_view(), name='driver-earnings'),

    # === 3. Автомобили водителя ===
    path('drivers/cars/', views.MyCarsListView.as_view(), name='my-cars-list'),
    path('drivers/cars/<int:id>/', views.MyCarDetailView.as_view(), name='my-car-detail'),
    path('drivers/cars/<int:id>/activate/', views.ActivateMyCarView.as_view(), name='my-car-activate'),
    path('drivers/offline/', views.GoOfflineView.as_view(), name='driver-offline'),
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

    # === 10. Чат ===
    path('trips/<uuid:id>/chat-room/', views.TripChatRoomView.as_view(), name='trip-chat-room'),
    path('trips/<uuid:trip_id>/messages/', views.ChatMessageListView.as_view(), name='chat-message-list'),
    path('trips/<uuid:trip_id>/messages/send/', views.ChatMessageCreateView.as_view(), name='chat-message-create'),

    # === 11. Trip Sharing ===
    path('trips/<uuid:trip_id>/share-token/', views.CreateTripShareTokenView.as_view(), name='create-trip-share-token'),
    path('trips/<uuid:trip_id>/share-tokens/', views.TripShareTokenListView.as_view(), name='trip-share-token-list'),
    path('trips/share/<uuid:token>/', views.PublicTripDetailView.as_view(), name='public-trip-detail'),

    # === 12. Admin Panel ===
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin-dashboard'),

    # Users
    path('admin/users/<int:id>/suspend/', views.AdminUserSuspendView.as_view(), name='admin-user-suspend'),

    # Drivers
    path('admin/drivers/', views.AdminDriverListView.as_view(), name='admin-driver-list'),
    path('admin/drivers/<int:id>/', views.AdminDriverDetailView.as_view(), name='admin-driver-detail'),
    path('admin/drivers/<int:id>/approve/', views.AdminDriverApproveView.as_view(), name='admin-driver-approve'),
    path('admin/drivers/<int:id>/suspend/', views.AdminDriverSuspendView.as_view(), name='admin-driver-suspend'),
    path('admin/drivers/<int:id>/reactivate/', views.AdminDriverReactivateView.as_view(), name='admin-driver-reactivate'),

    # Tariffs
    path('admin/tariffs/', views.AdminTariffListView.as_view(), name='admin-tariff-list'),
    path('admin/tariffs/<int:id>/', views.AdminTariffDetailView.as_view(), name='admin-tariff-detail'),

    # Trips
    path('admin/trips/', views.AdminTripListView.as_view(), name='admin-trip-list'),
    path('admin/trips/<uuid:id>/', views.AdminTripDetailView.as_view(), name='admin-trip-detail'),
    path('admin/trips/<uuid:id>/cancel/', views.AdminForceCancelTripView.as_view(), name='admin-trip-cancel'),
]
