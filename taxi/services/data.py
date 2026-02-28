from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from decimal import Decimal
from uuid import uuid4
from taxi.models import (
    Role, UserRole, DriverProfile,
    CarType, CarBrand, Car,
    Tariff, CarTypeTariff, CarLocation
)

User = get_user_model()

print("Cleaning old data...")
# Delete in reverse order to avoid foreign key constraint issues
CarLocation.objects.all().delete()
CarTypeTariff.objects.all().delete()
Car.objects.all().delete()
DriverProfile.objects.all().delete()
UserRole.objects.all().delete()
CarBrand.objects.all().delete()
CarType.objects.all().delete()
Tariff.objects.all().delete()
Role.objects.all().delete()
User.objects.all().delete()

print("Creating roles...")
customer_role = Role.objects.create(code="customer")
driver_role = Role.objects.create(code="driver")
admin_role = Role.objects.create(code="admin")

print("Creating car types...")
economy = CarType.objects.create(code="economy", description="Доступные авто")
comfort = CarType.objects.create(code="comfort", description="Комфорт класс")
premium = CarType.objects.create(code="premium", description="Премиум авто")
business = CarType.objects.create(code="business", description="Бизнес класс")

print("Creating tariffs...")
t1 = Tariff.objects.create(code="economy", base_price=600, price_per_km=90, price_per_min=15, min_price=600, is_active=True)
t2 = Tariff.objects.create(code="comfort", base_price=900, price_per_km=120, price_per_min=20, min_price=900, is_active=True)
t3 = Tariff.objects.create(code="premium", base_price=1800, price_per_km=200, price_per_min=35, min_price=1800, is_active=True)
t4 = Tariff.objects.create(code="business", base_price=3000, price_per_km=250, price_per_min=45, min_price=3000, is_active=True)

CarTypeTariff.objects.create(car_type=economy, tariff=t1)
CarTypeTariff.objects.create(car_type=comfort, tariff=t2)
CarTypeTariff.objects.create(car_type=premium, tariff=t3)
CarTypeTariff.objects.create(car_type=business, tariff=t4)

print("Creating car brands...")
brands = [
    ("Chevrolet Cobalt", "Chevrolet"),
    ("Lada Granta", "Lada"),
    ("Toyota Camry", "Toyota"),
    ("Hyundai Sonata", "Hyundai"),
    ("Kia K5", "Kia"),
]

brand_objects = []
for name, manufacturer in brands:
    brand_objects.append(CarBrand.objects.create(name=name, manufacturer=manufacturer))

print("Creating customers...")
customers = []
for i in range(1, 6):
    user = User.objects.create_user(
        phone=f"+7701000000{i}",
        password="test1234",
        first_name=f"Customer{i}",
        last_name="Test",
        is_verified=True,
        is_active=True
    )
    UserRole.objects.create(user=user, role=customer_role)
    customers.append(user)

print("Creating drivers...")
drivers = []
for i in range(1, 11):
    user = User.objects.create_user(
        phone=f"+7702000000{i}",
        password="test1234",
        first_name=f"Driver{i}",
        last_name="Test",
        is_verified=True,
        is_active=True,
        is_staff=True
    )
    UserRole.objects.create(user=user, role=driver_role)

    DriverProfile.objects.create(
        user=user,
        license_number=f"KZ-ALM-{100000+i}",
        experience_years=3 + i % 7,
        rating_avg=Decimal("4.5") + Decimal(i) / Decimal("100")
    )

    drivers.append(user)

# Astana street coordinates: (lat, lng, street_name)
# Left side (west of Ishim River) - 5 drivers
# Right side (east of Ishim River) - 5 drivers
astana_locations = [
    # Left side (West Bank)
    (51.143, 71.405, "Tauelsizdik Ave"),
    (51.140, 71.420, "Abay Ave"),
    (51.135, 71.410, "Respublika Ave"),
    (51.150, 71.400, "Saryarka Ave"),
    (51.145, 71.395, "Pobedy Ave"),
    # Right side (East Bank)
    (51.130, 71.450, "Korgalzhynskoe Highway"),
    (51.125, 71.430, "Turan Ave"),
    (51.120, 71.460, "Sansyzbay Ave"),
    (51.135, 71.470, "B. Momyshuly Ave"),
    (51.140, 71.480, "Moscow Ave"),
]

print("Creating cars with locations...")
cars = []
for idx, driver in enumerate(drivers):
    car = Car.objects.create(
        driver=driver,
        brand=brand_objects[idx % len(brand_objects)],
        car_type=[economy, comfort, premium, business][idx % 4],
        year=2020 + (idx % 5),
        plate_number=f"{100+idx}ALA02",
        is_active=True
    )
    cars.append(car)
    
    # Create car location for each driver
    lat, lng, street_name = astana_locations[idx]
    CarLocation.objects.create(
        car=car,
        lat=lat,
        lng=lng,
        location=Point(lng, lat),  # Point(x, y) = (lng, lat)
        speed_kmh=0,
        heading=0
    )
    print(f"  Driver {idx+1}: {street_name} ({lat}, {lng})")

print("SEED COMPLETED SUCCESSFULLY")
print("Customers:", UserRole.objects.filter(role=customer_role).count())
print("Drivers:", UserRole.objects.filter(role=driver_role).count())