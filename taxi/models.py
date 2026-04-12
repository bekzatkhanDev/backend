# models.py
import uuid
from django.contrib.gis.db import models as gis_models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('The Phone must be set')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
#        extra_fields.setdefault('
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.BigAutoField(primary_key=True)
    phone = models.CharField(max_length=15, unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.phone


class Role(models.Model):
    code = models.CharField(max_length=20, unique=True)  # customer, driver, admin

    def __str__(self):
        return self.code


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'role')
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'

    def __str__(self):
        return f"{self.user.phone} - {self.role.code}"


class DriverProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    license_number = models.CharField(max_length=50, unique=True)
    experience_years = models.PositiveSmallIntegerField()
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Driver: {self.user.phone}"


class CarType(models.Model):
    code = models.CharField(max_length=20, unique=True)  # economy, comfort, etc.
    description = models.TextField(blank=True)

    def __str__(self):
        return self.code


class CarBrand(models.Model):
    name = models.CharField(max_length=100)
    manufacturer = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Car(models.Model):
    id = models.BigAutoField(primary_key=True)
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cars')
    brand = models.ForeignKey(CarBrand, on_delete=models.PROTECT)
    car_type = models.ForeignKey(CarType, on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField()
    plate_number = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.brand.name} {self.plate_number}"


class CarLocation(gis_models.Model):
    car = gis_models.OneToOneField(Car, on_delete=gis_models.CASCADE, unique=True)
    lat = models.FloatField()
    lng = models.FloatField()
    location = gis_models.PointField(srid=4326, geography=True)
    speed_kmh = models.FloatField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Location of {self.car.plate_number}"


class Tariff(models.Model):
    code = models.CharField(max_length=50, unique=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_min = models.DecimalField(max_digits=10, decimal_places=2)
    min_price = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class CarTypeTariff(models.Model):
    car_type = models.ForeignKey(CarType, on_delete=models.CASCADE)
    tariff = models.ForeignKey(Tariff, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('car_type', 'tariff')

    def __str__(self):
        return f"{self.car_type.code} → {self.tariff.code}"


class Trip(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('on_route', 'On Route'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_trips')
    driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='driver_trips')
    car = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True)
    tariff = models.ForeignKey(Tariff, on_delete=models.PROTECT)
    start_lat = models.FloatField()
    start_lng = models.FloatField()
    end_lat = models.FloatField()
    end_lng = models.FloatField()
    distance_km = models.FloatField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_trips',
    )
    cancel_reason = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return f"Trip {self.id} – {self.customer.phone}"


class Review(models.Model):
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    reviewed = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.PositiveSmallIntegerField()  # 1–5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.reviewer.phone} for {self.reviewed.phone}"


class Payment(models.Model):
    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('kaspi', 'Kaspi Bank'),
        ('halyk', 'Halyk Bank'),
        ('freedom', 'Freedom Bank'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    trip = models.OneToOneField(Trip, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for {self.trip.id} – {self.status}"


class TripChatRoom(models.Model):
    """
    Chat room for a specific trip.
    Created only when a driver is assigned to the trip.
    """
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='chat_room')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Trip Chat Room'
        verbose_name_plural = 'Trip Chat Rooms'

    def __str__(self):
        return f"Chat room for Trip {self.trip.id}"


class ChatMessage(models.Model):
    """
    Individual message in a trip chat room.
    """
    chat_room = models.ForeignKey(TripChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'

    def __str__(self):
        return f"Message from {self.sender.phone} at {self.created_at}"


class TripShareToken(models.Model):
    """
    Shareable token for trip tracking.
    Allows anyone with the token to view trip status without authentication.
    """
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='share_tokens')
    token = models.UUIDField(unique=True, editable=False)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accessed_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Trip Share Token'
        verbose_name_plural = 'Trip Share Tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f"Share token for Trip {self.trip.id}"

    def save(self, *args, **kwargs):
        if not self.token:
            import uuid
            self.token = uuid.uuid4()
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    @classmethod
    def create_for_trip(cls, trip, hours_valid=24):
        """Create a new share token for a trip."""
        from django.utils import timezone
        expires_at = timezone.now() + timezone.timedelta(hours=hours_valid)
        return cls.objects.create(trip=trip, expires_at=expires_at)