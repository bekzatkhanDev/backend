import uuid
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import (
    User, Role, UserRole, DriverProfile, CarBrand, CarType,
    Car, CarLocation, Tariff, CarTypeTariff, Trip, Review, Payment
)
from django.conf import settings
from django.utils import timezone


# ======================
# Константы для сообщений об ошибках валидации
# ======================
PASSWORD_MISMATCH_ERROR = "Password fields didn't match."  # noqa: B105


# ======================
# 1. Аутентификация и пользователи
# ======================

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('phone', 'password', 'password2', 'first_name', 'last_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": PASSWORD_MISMATCH_ERROR})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        customer_role = Role.objects.get(code='customer')
        UserRole.objects.create(user=user, role=customer_role)
        return user


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)


class PasswordResetConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    token = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'phone', 'first_name', 'last_name', 'is_verified', 'roles')

    def get_roles(self, obj):
        return [ur.role.code for ur in obj.userrole_set.all()]


class AdminUserListSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'phone', 'first_name', 'last_name', 'is_active', 'roles')

    def get_roles(self, obj):
        return [ur.role.code for ur in obj.userrole_set.all()]


class AdminUserRoleUpdateSerializer(serializers.Serializer):
    roles = serializers.ListField(
        child=serializers.CharField(max_length=20),
        help_text="Список кодов ролей: ['customer', 'driver', 'admin']"
    )

    def validate_roles(self, value):
        valid_codes = set(Role.objects.values_list('code', flat=True))
        invalid = set(value) - valid_codes
        if invalid:
            raise serializers.ValidationError(f"Invalid roles: {invalid}")
        return value


# ======================
# 2. Профиль водителя
# ======================

class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = ('license_number', 'experience_years', 'rating_avg')
        read_only_fields = ('rating_avg',)


# ======================
# 3. Автомобили
# ======================

class CarBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarBrand
        fields = ('id', 'name', 'manufacturer')


class CarTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarType
        fields = ('id', 'code', 'description')


class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = ('id', 'code', 'base_price', 'price_per_km', 'price_per_min', 'min_price', 'is_active')


class CarSerializer(serializers.ModelSerializer):
    brand = CarBrandSerializer(read_only=True)
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=CarBrand.objects.all(), write_only=True, source='brand'
    )
    car_type = CarTypeSerializer(read_only=True)
    car_type_id = serializers.PrimaryKeyRelatedField(
        queryset=CarType.objects.all(), write_only=True, source='car_type'
    )

    class Meta:
        model = Car
        fields = (
            'id', 'brand', 'brand_id', 'car_type', 'car_type_id',
            'year', 'plate_number', 'is_active'
        )


# ======================
# 4. Геолокация
# ======================

class CarLocationSerializer(GeoFeatureModelSerializer):
    """Внутренний сериализатор для GeoDjango."""
    class Meta:
        model = CarLocation
        geo_field = "location"
        fields = ('car_id', 'lat', 'lng', 'speed_kmh', 'heading', 'updated_at')


class UpdateLocationSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    speed_kmh = serializers.FloatField(required=False, allow_null=True)
    heading = serializers.FloatField(required=False, allow_null=True)

    def validate_car_id(self, value):
        user = self.context['request'].user
        if not Car.objects.filter(id=value, driver=user).exists():
            raise serializers.ValidationError("Car not found or not owned by you.")
        return value


class NearbyCarsRequestSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    radius = serializers.FloatField(min_value=100, max_value=10000, default=5000)
    tariff_code = serializers.CharField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)


class NearbyCarSerializer(serializers.ModelSerializer):
    brand = serializers.CharField(source='brand.name')
    car_type = serializers.CharField(source='car_type.code')
    plate_number = serializers.CharField()
    distance_m = serializers.FloatField()

    class Meta:
        model = Car
        fields = ('id', 'brand', 'car_type', 'plate_number', 'distance_m')


# ======================
# 5. Расчёт стоимости и поездки
# ======================

class TripEstimateRequestSerializer(serializers.Serializer):
    start_lat = serializers.FloatField()
    start_lng = serializers.FloatField()
    end_lat = serializers.FloatField()
    end_lng = serializers.FloatField()
    tariff_id = serializers.IntegerField()

    def validate_tariff_id(self, value):
        if not Tariff.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Active tariff not found.")
        return value


class BulkTariffEstimateRequestSerializer(serializers.Serializer):
    start_lat = serializers.FloatField()
    start_lng = serializers.FloatField()
    end_lat = serializers.FloatField()
    end_lng = serializers.FloatField()


class TripEstimateResponseSerializer(serializers.Serializer):
    distance_km = serializers.FloatField()
    duration_min = serializers.FloatField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)


class TripCreateSerializer(serializers.Serializer):
    tariff_code = serializers.CharField()
    start_lat = serializers.FloatField()
    start_lng = serializers.FloatField()
    end_lat = serializers.FloatField()
    end_lng = serializers.FloatField()

    def validate_tariff_code(self, value):
        try:
            return Tariff.objects.get(code=value, is_active=True)
        except Tariff.DoesNotExist:
            raise serializers.ValidationError("Active tariff not found.")

    def validate(self, attrs):
        user = self.context['request'].user
        if Trip.objects.filter(
            customer=user,
            status__in=['requested', 'accepted', 'on_route']
        ).exists():
            raise serializers.ValidationError("You already have an active trip.")
        return attrs

    def create(self, validated_data):
        tariff = validated_data.pop('tariff_code')
        return Trip.objects.create(
            customer=self.context['request'].user,
            tariff=tariff,
            start_lat=validated_data['start_lat'],
            start_lng=validated_data['start_lng'],
            end_lat=validated_data['end_lat'],
            end_lng=validated_data['end_lng'],
            status='requested'
        )

class TripDetailSerializer(serializers.ModelSerializer):
    allowed_actions = serializers.SerializerMethodField()
    customer = UserProfileSerializer(read_only=True)
    driver = UserProfileSerializer(read_only=True)
    car = CarSerializer(read_only=True)
    tariff = TariffSerializer(read_only=True)

    class Meta:
        model = Trip
        fields = (
            'id', 'customer', 'driver', 'car', 'tariff',
            'start_lat', 'start_lng', 'end_lat', 'end_lng',
            'distance_km', 'price', 'status', 'created_at', 'allowed_actions'
        )

    def get_allowed_actions(self, obj):
        user = self.context['request'].user
        actions = []

        if obj.status == 'requested':
            if hasattr(user, 'driverprofile') and not obj.driver:
                actions.extend(['accept'])
            if obj.customer == user:
                actions.extend(['cancel'])

        elif obj.status == 'accepted' or obj.status == 'on_route':
            if obj.customer == user or obj.driver == user:
                actions.extend(['cancel'])

        return actions


class TripStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ('status',)

    def validate_status(self, value):
        instance = self.instance
        user = self.context['request'].user
        valid_transitions = {
            'requested': ['accepted', 'cancelled'],
            'accepted': ['on_route', 'cancelled'],
            'on_route': ['completed', 'cancelled'],
        }
        if instance.status not in valid_transitions:
            raise serializers.ValidationError("Invalid current status.")
        if value not in valid_transitions[instance.status]:
            raise serializers.ValidationError(f"Cannot transition from {instance.status} to {value}.")

        # Role/ownership enforcement
        is_admin = user.userrole_set.filter(role__code='admin').exists()
        is_driver = user.userrole_set.filter(role__code='driver').exists()
        is_customer = user.userrole_set.filter(role__code='customer').exists()

        if value == 'accepted':
            # Only a driver can accept an unassigned requested trip.
            if not (is_driver or is_admin):
                raise serializers.ValidationError("Only drivers can accept trips.")
            if instance.driver_id is not None:
                raise serializers.ValidationError("Trip is already assigned.")

            # Driver must be online (active car) and have a fresh location
            active_car = Car.objects.filter(driver=user, is_active=True).first()
            if not active_car:
                raise serializers.ValidationError("You must activate a car (go online) before accepting trips.")

            cutoff = timezone.now() - timezone.timedelta(
                seconds=getattr(settings, 'DRIVER_LOCATION_MAX_AGE_SECONDS', 60)
            )
            has_fresh_location = CarLocation.objects.filter(car=active_car, updated_at__gte=cutoff).exists()
            if not has_fresh_location:
                raise serializers.ValidationError("Your location is stale. Update location before accepting trips.")

        if value in ['on_route', 'completed']:
            if not (is_driver or is_admin):
                raise serializers.ValidationError("Only drivers can update trip progress.")
            if not is_admin and instance.driver_id != user.id:
                raise serializers.ValidationError("You are not assigned to this trip.")

        if value == 'cancelled':
            # Participants can cancel; admin can cancel any.
            if not is_admin and user not in [instance.customer, instance.driver]:
                raise serializers.ValidationError("Only trip participants can cancel.")

        return value

    def update(self, instance, validated_data):
        user = self.context['request'].user
        status = validated_data.get('status')
        if status == 'accepted':
            instance.driver = user
            instance.car = Car.objects.filter(driver=user, is_active=True).first()
        if status == 'cancelled':
            instance.cancelled_at = timezone.now()
            instance.cancelled_by = user
        instance.status = status
        instance.save()
        return instance


class TripCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


# ======================
# 6. Отзывы
# ======================

class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('reviewed', 'rating', 'comment')
        extra_kwargs = {
            'reviewed': {'required': True},
            'rating': {'min_value': 1, 'max_value': 5}
        }

    def validate(self, attrs):
        trip = self.context['trip']
        reviewer = self.context['request'].user

        # Только участники поездки могут оставить отзыв
        if reviewer not in [trip.customer, trip.driver]:
            raise serializers.ValidationError("You are not a participant of this trip.")

        # Нельзя оценить самого себя
        if attrs['reviewed'] == reviewer:
            raise serializers.ValidationError("You cannot review yourself.")

        # Уже существует отзыв на эту поездку?
        if Review.objects.filter(trip=trip).exists():
            raise serializers.ValidationError("Review for this trip already exists.")

        # Проверка: поездка завершена
        if trip.status != 'completed':
            raise serializers.ValidationError("Can only review completed trips.")

        return attrs


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = UserProfileSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'reviewer', 'rating', 'comment', 'created_at')


# ======================
# 7. Оплата
# ======================

class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('trip', 'method')
        extra_kwargs = {'trip': {'required': True}}

    def validate_trip(self, value):
        user = self.context['request'].user
        
        # Платёж может создать только пассажир поездки
        if value.customer != user:
            raise serializers.ValidationError("You can only pay for your own trips.")
        
        # Оплата только по завершённой поездке
        if value.status != 'completed':
            raise serializers.ValidationError("Payment can only be made for completed trips.")
        
        if hasattr(value, 'payment'):
            raise serializers.ValidationError("Payment for this trip already exists.")
        if Payment.objects.filter(trip=value).exists():
            raise serializers.ValidationError("Payment for this trip already exists.")
        
        return value


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'trip', 'amount', 'method', 'status', 'created_at')
        read_only_fields = ('amount', 'status')