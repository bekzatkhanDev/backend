import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, generics, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import (
    User, Role, UserRole, DriverProfile, Car, CarLocation, CarBrand, CarType,
    Tariff, CarTypeTariff, Trip, Review, Payment
)
from .serializers import (
    RegisterSerializer, LoginResponseSerializer, RefreshTokenSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    UserProfileSerializer, AdminUserListSerializer, AdminUserRoleUpdateSerializer,
    DriverProfileSerializer, CarSerializer, CarBrandSerializer, CarTypeSerializer,CarLocationSerializer,
    TariffSerializer, UpdateLocationSerializer, NearbyCarsRequestSerializer,
    NearbyCarSerializer, TripEstimateRequestSerializer, TripEstimateResponseSerializer,
    TripCreateSerializer, TripDetailSerializer, TripStatusUpdateSerializer,
    TripCancelSerializer, ReviewCreateSerializer, ReviewSerializer,
    PaymentCreateSerializer, PaymentSerializer, BulkTariffEstimateRequestSerializer
)
from .permissions import (
    IsAuthenticatedAndActive, IsAdmin, IsCustomer, IsDriver,
    IsOwnerOrAdmin, IsTripParticipantOrAdmin, IsActiveDriver, IsCarOwner,
    ReadOnlyForAll, has_role
)
from .services import get_routing_service
from .services.pricing import PriceCalculator

logger = logging.getLogger(__name__)


# ======================
# 1. Аутентификация
# ======================

class RegisterView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone')
        password = request.data.get('password')
        password2 = request.data.get('password2')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        role_code = request.data.get('role', 'customer')

        # Валидация паролей
        if password != password2:
            return Response(
                {'error': 'Passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Валидация роли (теперь опционально)
        allowed_roles = ['customer', 'driver']
        if role_code and role_code not in allowed_roles:
            return Response(
                {'error': f'Role must be one of: {", ".join(allowed_roles)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not role_code:
            role_code = 'customer'

        # Проверка уникальности телефона
        if User.objects.filter(phone=phone).exists():
            return Response(
                {'error': 'User with this phone already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Создаём пользователя
                user = User.objects.create_user(
                    phone=phone,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,
                    is_verified=False  # если используется подтверждение
                )

                # Назначаем роль
                role = Role.objects.get(code=role_code)
                UserRole.objects.create(user=user, role=role)

                # Профиль водителя создаётся отдельно при первом PATCH /drivers/profile/

        except Role.DoesNotExist:
            return Response(
                {'error': 'Internal error: role not found'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {'error': 'Registration failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'id': user.id,
            'phone': user.phone,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'roles': [role_code]
        }, status=status.HTTP_201_CREATED)


class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone')
        password = request.data.get('password')

        user = User.objects.filter(phone=phone).first()
        if not (user and user.check_password(password) and user.is_active):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        # Получаем коды ролей через M2M связь
        roles = list(
            user.userrole_set.select_related('role')
            .values_list('role__code', flat=True)
        )

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'phone': user.phone,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'roles': roles,
            }
        }, status=status.HTTP_200_OK)

class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = RefreshTokenSerializer


class LogoutView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # TODO: отправить SMS/email с кодом сброса
        logger.info(f"Password reset requested for {serializer.validated_data['phone']}")
        return Response({"detail": "If your phone exists, you will receive a reset code."})


class PasswordResetConfirmView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # TODO: проверить код из SMS и обновить пароль
        phone = serializer.validated_data['phone']
        new_password = serializer.validated_data['new_password']
        user = get_object_or_404(User, phone=phone)
        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password has been reset."})


# ======================
# 2. Пользователи и профили
# ======================

class CurrentUserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticatedAndActive]

    def get_object(self):
        return self.request.user


class AdminUserListView(generics.ListAPIView):
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAuthenticatedAndActive, IsAdmin]
    queryset = User.objects.all()


class AdminUserDetailView(generics.RetrieveAPIView):
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAuthenticatedAndActive, IsAdmin]
    lookup_field = 'id'
    queryset = User.objects.all()


class AdminUserRoleUpdateView(views.APIView):
    permission_classes = [IsAuthenticatedAndActive, IsAdmin]

    def patch(self, request, id):
        user = get_object_or_404(User, id=id)
        serializer = AdminUserRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        codes = serializer.validated_data['roles']
        roles = Role.objects.filter(code__in=codes)
        UserRole.objects.filter(user=user).delete()
        UserRole.objects.bulk_create([
            UserRole(user=user, role=role) for role in roles
        ])
        return Response({"roles": codes})


# ======================
# 3. Профиль водителя
# ======================

class DriverProfileCreateView(generics.CreateAPIView):
    serializer_class = DriverProfileSerializer
    permission_classes = [IsAuthenticatedAndActive, IsDriver]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class DriverProfileMeView(generics.RetrieveUpdateAPIView):
    serializer_class = DriverProfileSerializer
    permission_classes = [IsAuthenticatedAndActive, IsDriver]

    def get_object(self):
        return self.request.user.driverprofile


# ======================
# 4. Автомобили
# ======================

class MyCarsListView(generics.ListCreateAPIView):
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticatedAndActive, IsDriver]

    def get_queryset(self):
        return Car.objects.filter(driver=self.request.user)

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user)


class MyCarDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticatedAndActive, IsDriver, IsCarOwner]

    def get_queryset(self):
        return Car.objects.filter(driver=self.request.user)


class ActivateMyCarView(views.APIView):
    """
    Driver chooses which car is active (online).
    Ensures only one active car per driver.
    """
    permission_classes = [IsAuthenticatedAndActive, IsDriver]

    def post(self, request, id):
        car = get_object_or_404(Car, id=id, driver=request.user)

        with transaction.atomic():
            Car.objects.filter(driver=request.user, is_active=True).exclude(id=car.id).update(is_active=False)
            if not car.is_active:
                car.is_active = True
                car.save(update_fields=['is_active'])

        return Response({'status': 'ok', 'active_car_id': car.id}, status=status.HTTP_200_OK)


class GoOfflineView(views.APIView):
    """Driver goes offline by deactivating all cars."""
    permission_classes = [IsAuthenticatedAndActive, IsDriver]

    def post(self, request):
        Car.objects.filter(driver=request.user, is_active=True).update(is_active=False)
        return Response({'status': 'ok', 'online': False}, status=status.HTTP_200_OK)


class DriverOnlineStatusView(views.APIView):
    """
    Returns driver online status + active car + last location freshness.

    Useful for driver app bootstrapping:
    - decide whether to show "Go online" or "Go offline"
    - prompt user to enable location updates if stale
    """
    permission_classes = [IsAuthenticatedAndActive, IsDriver]

    def get(self, request):
        user = request.user
        active_car = Car.objects.filter(driver=user, is_active=True).select_related('brand', 'car_type').first()

        max_age = getattr(settings, 'DRIVER_LOCATION_MAX_AGE_SECONDS', 60)
        cutoff = timezone.now() - timezone.timedelta(seconds=max_age)

        last_location = None
        location_is_stale = True

        if active_car:
            last_location = CarLocation.objects.filter(car=active_car).order_by('-updated_at').first()
            if last_location and last_location.updated_at and last_location.updated_at >= cutoff:
                location_is_stale = False

        return Response({
            'online': bool(active_car),
            'active_car': {
                'id': active_car.id,
                'plate_number': active_car.plate_number,
                'brand': active_car.brand.name,
                'car_type': active_car.car_type.code,
                'year': active_car.year,
            } if active_car else None,
            'last_location': {
                'lat': last_location.lat,
                'lng': last_location.lng,
                'updated_at': last_location.updated_at,
            } if last_location else None,
            'location_is_stale': location_is_stale,
            'location_max_age_seconds': int(max_age),
        }, status=status.HTTP_200_OK)


class DriverDashboardView(views.APIView):
    """
    Single endpoint for driver app bootstrap.

    Returns:
    - user + driver profile
    - driver cars (including which one is active)
    - online-status (active car + last location freshness)
    - active trip if exists (assigned trip)
    """
    permission_classes = [IsAuthenticatedAndActive, IsDriver]

    def get(self, request):
        user = request.user

        # Profiles
        user_data = UserProfileSerializer(user, context={'request': request}).data
        driver_profile = getattr(user, 'driverprofile', None)
        driver_profile_data = (
            DriverProfileSerializer(driver_profile, context={'request': request}).data
            if driver_profile else None
        )

        # Cars
        cars_qs = Car.objects.filter(driver=user).select_related('brand', 'car_type').order_by('-is_active', 'id')
        cars_data = CarSerializer(cars_qs, many=True, context={'request': request}).data

        # Online status + last location
        active_car = cars_qs.filter(is_active=True).first()
        max_age = getattr(settings, 'DRIVER_LOCATION_MAX_AGE_SECONDS', 60)
        cutoff = timezone.now() - timezone.timedelta(seconds=max_age)

        last_location = None
        location_is_stale = True
        if active_car:
            last_location = CarLocation.objects.filter(car=active_car).order_by('-updated_at').first()
            if last_location and last_location.updated_at and last_location.updated_at >= cutoff:
                location_is_stale = False

        # Active trip (driver side)
        active_trip = Trip.objects.filter(driver=user, status__in=['accepted', 'on_route']).first()
        active_trip_data = (
            TripDetailSerializer(active_trip, context={'request': request}).data
            if active_trip else None
        )

        return Response({
            'user': user_data,
            'driver_profile': driver_profile_data,
            'cars': cars_data,
            'online_status': {
                'online': bool(active_car),
                'active_car_id': active_car.id if active_car else None,
                'last_location': {
                    'lat': last_location.lat,
                    'lng': last_location.lng,
                    'updated_at': last_location.updated_at,
                } if last_location else None,
                'location_is_stale': location_is_stale,
                'location_max_age_seconds': int(max_age),
            },
            'active_trip': active_trip_data,
        }, status=status.HTTP_200_OK)


class DriverEarningsView(views.APIView):
    """
    Driver earnings summary derived from completed trips and payments.

    Query params:
      - from: ISO date/datetime (optional)
      - to: ISO date/datetime (optional)

    Notes:
      - "gross" is sum of Trip.price for completed trips
      - "paid" is sum of Payment.amount where payment.status='paid'
      - "unpaid" is gross - paid (includes pending/failed/no payment)
    """
    permission_classes = [IsAuthenticatedAndActive, IsDriver]

    def get(self, request):
        user = request.user
        qs = Trip.objects.filter(driver=user, status='completed')

        date_from = request.query_params.get('from')
        date_to = request.query_params.get('to')

        if date_from:
            try:
                dt_from = timezone.datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                if timezone.is_naive(dt_from):
                    dt_from = timezone.make_aware(dt_from, timezone.get_current_timezone())
                qs = qs.filter(created_at__gte=dt_from)
            except Exception:
                return Response({'error': 'Invalid from date. Use ISO format.'}, status=status.HTTP_400_BAD_REQUEST)

        if date_to:
            try:
                dt_to = timezone.datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                if timezone.is_naive(dt_to):
                    dt_to = timezone.make_aware(dt_to, timezone.get_current_timezone())
                qs = qs.filter(created_at__lte=dt_to)
            except Exception:
                return Response({'error': 'Invalid to date. Use ISO format.'}, status=status.HTTP_400_BAD_REQUEST)

        agg = qs.aggregate(
            trips_completed=Count('id'),
            gross=Sum('price'),
        )
        gross = agg['gross'] or Decimal('0.00')
        trips_completed = agg['trips_completed'] or 0

        paid_qs = Payment.objects.filter(trip__in=qs, status='paid')
        paid_agg = paid_qs.aggregate(paid=Sum('amount'))
        paid = paid_agg['paid'] or Decimal('0.00')

        unpaid = gross - paid
        if unpaid < 0:
            unpaid = Decimal('0.00')

        return Response({
            'trips_completed': trips_completed,
            'gross': float(gross),
            'paid': float(paid),
            'unpaid': float(unpaid),
            'currency': 'KZT',
            'range': {
                'from': date_from,
                'to': date_to,
            }
        }, status=status.HTTP_200_OK)


class AdminCarDetailView(generics.RetrieveAPIView):
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticatedAndActive, IsAdmin]
    queryset = Car.objects.all()


# ======================
# 5. Справочники
# ======================

class CarBrandListView(generics.ListAPIView):
    serializer_class = CarBrandSerializer
    permission_classes = [AllowAny]
    queryset = CarBrand.objects.all()


class CarTypeListView(generics.ListAPIView):
    serializer_class = CarTypeSerializer
    permission_classes = [AllowAny]
    queryset = CarType.objects.all()


class TariffListView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TariffSerializer
        return TariffSerializer

    def get_queryset(self):
        if self.request.method == 'GET':
            return Tariff.objects.filter(is_active=True)
        return Tariff.objects.all()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticatedAndActive(), IsAdmin()]


class TariffDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = TariffSerializer
    permission_classes = [IsAuthenticatedAndActive, IsAdmin]
    queryset = Tariff.objects.all()


# ======================
# 6. Геолокация
# ======================

class UpdateLocationView(views.APIView):
    permission_classes = [IsAuthenticatedAndActive, IsDriver, IsActiveDriver]

    def post(self, request):
        serializer = UpdateLocationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        car_id = serializer.validated_data['car_id']
        lat = serializer.validated_data['lat']
        lng = serializer.validated_data['lng']
        point = Point(lng, lat, srid=4326)

        CarLocation.objects.update_or_create(
            car_id=car_id,
            defaults={
                'lat': lat,
                'lng': lng,
                'location': point,
                'speed_kmh': serializer.validated_data.get('speed_kmh'),
                'heading': serializer.validated_data.get('heading'),
            }
        )
        return Response({"status": "Location updated"}, status=status.HTTP_200_OK)


class MyLocationView(generics.RetrieveAPIView):
    serializer_class = CarLocationSerializer
    permission_classes = [IsAuthenticatedAndActive, IsDriver]

    def get_object(self):
        car = Car.objects.filter(driver=self.request.user, is_active=True).first()
        if not car:
            return None
        obj, _ = CarLocation.objects.get_or_create(car=car)
        return obj


class NearbyCarsView(views.APIView):
    permission_classes = [IsAuthenticatedAndActive, IsCustomer]

    def get(self, request):
        serializer = NearbyCarsRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        lat = serializer.validated_data['lat']
        lng = serializer.validated_data['lng']
        radius = serializer.validated_data['radius']
        tariff_code = serializer.validated_data.get('tariff_code')
        limit = serializer.validated_data['limit']

        point = Point(lng, lat, srid=4326)

        cutoff = timezone.now() - timezone.timedelta(
            seconds=getattr(settings, 'DRIVER_LOCATION_MAX_AGE_SECONDS', 60)
        )

        queryset = Car.objects.filter(
            is_active=True,
            carlocation__isnull=False,
            carlocation__updated_at__gte=cutoff,
        ).select_related('brand', 'car_type', 'driver', 'carlocation')

        if tariff_code:
            queryset = queryset.filter(
                car_type__cartypetariff__tariff__code=tariff_code,
                car_type__cartypetariff__tariff__is_active=True
            )

        queryset = queryset.annotate(
            distance_m=Distance('carlocation__location', point)
        ).filter(
            distance_m__lte=radius
        ).order_by('distance_m')[:limit]

        cars = []
        for car in queryset:
            driver_id = car.driver.id if car.driver else None
            cars.append({
                'id': car.id,
                'driver_id': driver_id,
                'car_id': car.id,
                'lat': car.carlocation.lat,
                'lng': car.carlocation.lng,
                'distance_km': round(float(car.distance_m.m) / 1000, 2),
                'brand': car.brand.name,
                'car_type': car.car_type.code,
                'plate_number': car.plate_number,
                'distance_m': float(car.distance_m.m),
            })

        return Response(cars)


# ======================
# 7. Расчёт стоимости
# ======================

class TripEstimateView(views.APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request):
        serializer = TripEstimateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_lat = serializer.validated_data['start_lat']
        start_lng = serializer.validated_data['start_lng']
        end_lat = serializer.validated_data['end_lat']
        end_lng = serializer.validated_data['end_lng']
        tariff_id = serializer.validated_data['tariff_id']

        tariff = Tariff.objects.get(id=tariff_id)
        calculator = PriceCalculator(tariff)
        estimate = calculator.calculate_estimate(start_lat, start_lng, end_lat, end_lng)

        return Response(estimate)


class BulkTariffEstimateView(views.APIView):
    """Расчёт стоимости по всем активным тарифам для экрана выбора тарифа."""
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request):
        serializer = BulkTariffEstimateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_lat = serializer.validated_data['start_lat']
        start_lng = serializer.validated_data['start_lng']
        end_lat = serializer.validated_data['end_lat']
        end_lng = serializer.validated_data['end_lng']

        tariffs = Tariff.objects.filter(is_active=True)

        if not tariffs.exists():
            return Response(
                {'error': 'No active tariffs found'},
                status=status.HTTP_404_NOT_FOUND
            )

        routing_service = get_routing_service()
        route_info = routing_service.get_route(
            start_lng=start_lng,
            start_lat=start_lat,
            end_lng=end_lng,
            end_lat=end_lat
        )

        distance_km = route_info['distance_km']
        duration_min = route_info['duration_min']

        estimates = []
        for tariff in tariffs:
            calculator = PriceCalculator(tariff)
            price = calculator.calculate_price(distance_km, duration_min)

            estimates.append({
                'tariff_id': tariff.id,
                'tariff_code': tariff.code,
                'base_price': float(tariff.base_price),
                'price_per_km': float(tariff.price_per_km),
                'price_per_min': float(tariff.price_per_min),
                'min_price': float(tariff.min_price),
                'distance_km': distance_km,
                'duration_min': duration_min,
                'estimated_price': float(price),
            })

        estimates.sort(key=lambda x: x['estimated_price'])

        return Response({
            'distance_km': distance_km,
            'duration_min': duration_min,
            'estimates': estimates,
            'is_estimate': route_info.get('is_estimate', False),
        })

# ======================
# 8. Поездки
# ======================

class TripCreateView(generics.CreateAPIView):
    serializer_class = TripCreateSerializer
    permission_classes = [IsAuthenticatedAndActive, IsCustomer]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            logger.error(f"Trip creation validation errors: {serializer.errors}")
            return Response(
                {'error': 'Validation failed', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tariff = serializer.validated_data['tariff_code']
        start_lat = serializer.validated_data['start_lat']
        start_lng = serializer.validated_data['start_lng']
        end_lat = serializer.validated_data['end_lat']
        end_lng = serializer.validated_data['end_lng']
        
        calculator = PriceCalculator(tariff)
        estimate = calculator.calculate_estimate(start_lat, start_lng, end_lat, end_lng)
        
        price = Decimal(str(estimate['price']))
        
        trip = Trip.objects.create(
            customer=request.user,
            tariff=tariff,
            start_lat=start_lat,
            start_lng=start_lng,
            end_lat=end_lat,
            end_lng=end_lng,
            distance_km=estimate['distance_km'],
            price=price,
            status='requested'
        )

        trip = self._assign_nearest_driver(trip)

        response_data = {
            'id': trip.id,
            'status': trip.status,
            'distance_km': estimate['distance_km'],
            'price': float(price)
        }
        if trip.driver:
            response_data['driver'] = {
                'id': trip.driver.id,
                'phone': trip.driver.phone,
                'first_name': trip.driver.first_name,
            }
            response_data['car'] = {
                'id': trip.car.id,
                'brand': trip.car.brand.name,
                'plate_number': trip.car.plate_number,
            }

        return Response(response_data, status=status.HTTP_201_CREATED)

    def _assign_nearest_driver(self, trip):
        """Назначаем ближайшего свободного водителя на поездку."""
        from django.contrib.gis.db.models.functions import Distance

        busy_driver_ids = Trip.objects.filter(
            status__in=['requested', 'accepted', 'on_route']
        ).exclude(driver__isnull=True).values_list('driver_id', flat=True)
        busy_driver_ids = set(busy_driver_ids)

        tariff = trip.tariff
        car_type_ids = CarTypeTariff.objects.filter(
            tariff=tariff
        ).values_list('car_type_id', flat=True)

        point = Point(trip.start_lng, trip.start_lat, srid=4326)

        cutoff = timezone.now() - timezone.timedelta(
            seconds=getattr(settings, 'DRIVER_LOCATION_MAX_AGE_SECONDS', 60)
        )

        available_cars = Car.objects.filter(
            is_active=True,
            carlocation__isnull=False,
            carlocation__updated_at__gte=cutoff,
            car_type_id__in=car_type_ids
        ).exclude(
            driver_id__in=busy_driver_ids
        ).select_related('brand', 'car_type', 'driver')

        if not available_cars.exists():
            logger.info(f"Trip {trip.id}: No available drivers found")
            return trip

        available_cars = available_cars.annotate(
            distance_m=Distance('carlocation__location', point)
        ).order_by('distance_m')

        nearest_car = available_cars.first()

        if nearest_car:
            trip.driver = nearest_car.driver
            trip.car = nearest_car
            trip.status = 'accepted'
            trip.save(update_fields=['driver', 'car', 'status'])
            logger.info(f"Trip {trip.id}: Assigned to driver {trip.driver.phone} (car: {nearest_car.plate_number})")
        else:
            logger.info(f"Trip {trip.id}: No available cars after filtering")

        return trip


class ActiveTripView(generics.RetrieveAPIView):
    serializer_class = TripDetailSerializer
    permission_classes = [IsAuthenticatedAndActive]

    def get_object(self):
        user = self.request.user
        trip = Trip.objects.filter(
            customer=user,
            status__in=['requested', 'accepted', 'on_route']
        ).first()
        if not trip:
            trip = Trip.objects.filter(
                driver=user,
                status__in=['accepted', 'on_route']
            ).first()
        if not trip:
            from rest_framework.exceptions import NotFound
            raise NotFound("Нет активной поездки.")
        return trip


class TripDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = TripDetailSerializer
    permission_classes = [IsAuthenticatedAndActive, IsTripParticipantOrAdmin]
    lookup_field = 'id'
    queryset = Trip.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return TripStatusUpdateSerializer
        return TripDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_status = instance.status
        
        response = super().update(request, *args, **kwargs)
        
        if response.status_code == 200:
            instance.refresh_from_db()
            if old_status != 'completed' and instance.status == 'completed':
                calculator = PriceCalculator(instance.tariff)
                estimate = calculator.calculate_estimate(
                    instance.start_lat,
                    instance.start_lng,
                    instance.end_lat,
                    instance.end_lng
                )
                
                instance.distance_km = estimate['distance_km']
                instance.price = Decimal(str(estimate['price']))
                instance.save(update_fields=['distance_km', 'price'])
                response.data['distance_km'] = estimate['distance_km']
                response.data['price'] = estimate['price']
        
        return response


class TripHistoryView(generics.ListAPIView):
    serializer_class = TripDetailSerializer
    permission_classes = [IsAuthenticatedAndActive]

    def get_queryset(self):
        user = self.request.user
        role_filter = self.request.query_params.get('role')
        status_filter = self.request.query_params.get('status')
        date_from = self.request.query_params.get('date_from')

        qs = Trip.objects.none()
        if role_filter == 'driver' or (not role_filter and has_role(user, 'driver')):
            qs = Trip.objects.filter(driver=user)
        if role_filter == 'customer' or (not role_filter and has_role(user, 'customer')):
            qs = Trip.objects.filter(customer=user)
        if has_role(user, 'admin'):
            qs = Trip.objects.all()

        if status_filter:
            qs = qs.filter(status=status_filter)
        if date_from:
            qs = qs.filter(created_at__gte=date_from)

        return qs.order_by('-created_at')


class CancelTripView(views.APIView):
    permission_classes = [IsAuthenticatedAndActive, IsTripParticipantOrAdmin]

    def post(self, request, id):
        trip = get_object_or_404(Trip, id=id)
        serializer = TripCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip.status = 'cancelled'
        trip.cancelled_at = timezone.now()
        trip.cancelled_by = request.user
        trip.cancel_reason = serializer.validated_data.get('reason', '') or ''
        trip.save(update_fields=['status', 'cancelled_at', 'cancelled_by', 'cancel_reason'])
        return Response({"status": "Trip cancelled"})


# ======================
# 9. Отзывы
# ======================

class CreateReviewView(views.APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request, id):
        trip = get_object_or_404(Trip, id=id)

        if not (
            has_role(request.user, 'admin') or
            request.user in [trip.customer, trip.driver]
        ):
            return Response(
                {"detail": "You are not a participant of this trip."},
                status=status.HTTP_403_FORBIDDEN
            )

        if trip.status != 'completed':
            return Response(
                {"error": "Only completed trips can be reviewed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReviewCreateSerializer(
            data=request.data,
            context={'trip': trip, 'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(trip=trip, reviewer=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class UserReviewsView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedAndActive]

    def get_queryset(self):
        user_id = self.kwargs['id']
        user = get_object_or_404(User, id=user_id)
        return Review.objects.filter(reviewed=user).select_related('reviewer')


# ======================
# 10. Оплата
# ======================

class CreatePaymentView(generics.CreateAPIView):
    serializer_class = PaymentCreateSerializer
    permission_classes = [IsAuthenticatedAndActive, IsCustomer]

    def perform_create(self, serializer):
        trip = serializer.validated_data['trip']
        amount = trip.price
        payment = Payment.objects.create(
            trip=trip,
            amount=amount,
            method=serializer.validated_data['method'],
            status='pending'
        )
        serializer.instance = payment


class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticatedAndActive, IsTripParticipantOrAdmin]
    queryset = Payment.objects.select_related('trip')


class PaymentByTripView(generics.RetrieveAPIView):
    """Платёж по ID поездки."""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticatedAndActive, IsTripParticipantOrAdmin]
    
    def get_object(self):
        trip_id = self.kwargs.get('trip_id')
        trip = get_object_or_404(Trip, id=trip_id)
        payment = Payment.objects.filter(trip=trip).first()
        if not payment:
            from rest_framework.exceptions import NotFound
            raise NotFound({"detail": "No payment found for this trip."})
        return payment
    
    def get_queryset(self):
        return Payment.objects.select_related('trip')
