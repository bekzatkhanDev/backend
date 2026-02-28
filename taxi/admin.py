from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    User, Role, UserRole, DriverProfile, CarBrand, CarType,
    Car, CarLocation, Tariff, CarTypeTariff, Trip, Review, Payment
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ( 'phone', 'first_name', 'last_name', 'is_active', 'is_verified', 'roles_display')
    list_filter = ('is_active', 'is_verified', 'is_staff', 'userrole__role')
    search_fields = ('phone', 'first_name', 'last_name')
    ordering = ('phone',)
    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'password1', 'password2'),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ()

    def roles_display(self, obj):
        return ", ".join([ur.role.code for ur in obj.userrole_set.all()])
    roles_display.short_description = 'Roles'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('userrole_set__role')


class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('code',)
    search_fields = ('code',)


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ('user_phone', 'license_number', 'experience_years', 'rating_avg')
    list_filter = ('experience_years',)
    search_fields = ('user__phone', 'license_number')
    raw_id_fields = ('user',)

    def user_phone(self, obj):
        return obj.user.phone
    user_phone.short_description = 'Phone'
    user_phone.admin_order_field = 'user__phone'


@admin.register(CarBrand)
class CarBrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'manufacturer')
    search_fields = ('name',)


@admin.register(CarType)
class CarTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'description')
    search_fields = ('code',)


class CarLocationInline(admin.TabularInline):
    model = CarLocation
    extra = 0
    readonly_fields = ('updated_at',)
    modifiable = False  # только просмотр в инлайне


@admin.register(Car)
class CarAdmin(OSMGeoAdmin):
    list_display = ('plate_number', 'driver_phone', 'brand', 'car_type', 'year', 'is_active')
    list_filter = ('is_active', 'brand', 'car_type', 'year')
    search_fields = ('plate_number', 'driver__phone')
    raw_id_fields = ('driver',)
    inlines = [CarLocationInline]

    def driver_phone(self, obj):
        return obj.driver.phone if obj.driver else '-'
    driver_phone.short_description = 'Driver'
    driver_phone.admin_order_field = 'driver__phone'


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('code', 'base_price', 'price_per_km', 'price_per_min', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code',)


@admin.register(CarTypeTariff)
class CarTypeTariffAdmin(admin.ModelAdmin):
    list_display = ('car_type', 'tariff')
    list_filter = ('car_type', 'tariff')


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_phone', 'driver_phone', 'status', 'price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('customer__phone', 'driver__phone')
    raw_id_fields = ('customer', 'driver', 'car', 'tariff')
    readonly_fields = ('id',)

    def customer_phone(self, obj):
        return obj.customer.phone if obj.customer else '-'
    customer_phone.short_description = 'Customer'

    def driver_phone(self, obj):
        return obj.driver.phone if obj.driver else '-'
    driver_phone.short_description = 'Driver'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('trip_id', 'reviewer_phone', 'reviewed_phone', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('reviewer__phone', 'reviewed__phone')
    raw_id_fields = ('trip', 'reviewer', 'reviewed')

    def trip_id(self, obj):
        return str(obj.trip.id)[:8]
    trip_id.short_description = 'Trip (short ID)'

    def reviewer_phone(self, obj):
        return obj.reviewer.phone
    reviewer_phone.short_description = 'Reviewer'

    def reviewed_phone(self, obj):
        return obj.reviewed.phone
    reviewed_phone.short_description = 'Reviewed'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'trip_id', 'amount', 'method', 'status', 'created_at')
    list_filter = ('method', 'status', 'created_at')
    raw_id_fields = ('trip',)
    readonly_fields = ('id',)

    def trip_id(self, obj):
        return str(obj.trip.id)[:8]
    trip_id.short_description = 'Trip (short ID)'