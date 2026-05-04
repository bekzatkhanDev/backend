from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from taxi.models import (
    Role, UserRole, DriverProfile,
    CarType, CarBrand, Car,
    Tariff, CarTypeTariff, CarLocation,
    Trip, Review,
)

User = get_user_model()

TRIP_ROUTES = [
    (51.143, 71.405, 51.130, 71.450, 5.2),
    (51.140, 71.420, 51.125, 71.430, 2.8),
    (51.135, 71.410, 51.138, 71.475, 7.4),
    (51.150, 71.400, 51.140, 71.480, 9.1),
    (51.145, 71.395, 51.120, 71.460, 8.3),
    (51.138, 71.415, 51.133, 71.455, 5.7),
    (51.148, 71.408, 51.118, 71.435, 6.9),
    (51.142, 71.425, 51.145, 71.455, 4.1),
    (51.136, 71.400, 51.127, 71.470, 8.8),
    (51.155, 71.390, 51.115, 71.450, 9.5),
    (51.130, 71.405, 51.132, 71.465, 7.2),
    (51.152, 71.385, 51.122, 71.440, 7.9),
]

ASTANA_LOCATIONS = [
    (51.143, 71.405, "Tauelsizdik Ave"),
    (51.140, 71.420, "Abay Ave"),
    (51.135, 71.410, "Respublika Ave"),
    (51.150, 71.400, "Saryarka Ave"),
    (51.145, 71.395, "Pobedy Ave"),
    (51.138, 71.415, "Dostyk Ave"),
    (51.148, 71.408, "Ken Dala Ave"),
    (51.142, 71.425, "Bogenbay Batyr"),
    (51.136, 71.400, "Orynbor Street"),
    (51.155, 71.390, "Kunayeva Street"),
    (51.130, 71.405, "M. Gabitova Street"),
    (51.152, 71.385, "A. Imanova Street"),
    (51.137, 71.430, "Qabanbay Batyr Ave"),
    (51.147, 71.415, "S. Seifullin Street"),
    (51.141, 71.390, "Zheltoksan Street"),
    (51.130, 71.450, "Korgalzhynskoe Highway"),
    (51.125, 71.430, "Turan Ave"),
    (51.120, 71.460, "Sansyzbay Ave"),
    (51.135, 71.470, "B. Momyshuly Ave"),
    (51.140, 71.480, "Moscow Ave"),
    (51.128, 71.455, "A. Qunanbayuli Street"),
    (51.132, 71.465, "E. Aerodromnaya Street"),
    (51.122, 71.440, "V. Kosenko Street"),
    (51.138, 71.475, "K. Satpayev Street"),
    (51.115, 71.450, "S. Toraigyrov Street"),
    (51.133, 71.455, "U. Dzholdasbekov Street"),
    (51.127, 71.470, "A. Pushkin Street"),
    (51.142, 71.460, "M. Gorky Street"),
    (51.118, 71.435, "Zh. N. Qozybaev Street"),
    (51.145, 71.455, "E. Bukin Street"),
]


def _make_trip(now, customer, driver, car, tariff, route_idx, days_ago, hours_offset=0, status='completed'):
    r = TRIP_ROUTES[route_idx % len(TRIP_ROUTES)]
    price = Decimal(str(round(float(tariff.base_price) + r[4] * float(tariff.price_per_km), 2)))
    trip = Trip.objects.create(
        customer=customer,
        driver=driver,
        car=car,
        tariff=tariff,
        start_lat=r[0], start_lng=r[1],
        end_lat=r[2], end_lng=r[3],
        distance_km=r[4],
        price=price,
        status=status,
    )
    created = now - timedelta(days=days_ago, hours=hours_offset)
    update_kwargs = {'created_at': created}
    if status == 'cancelled':
        update_kwargs['cancelled_at'] = created + timedelta(minutes=5)
    Trip.objects.filter(pk=trip.pk).update(**update_kwargs)
    return trip


class Command(BaseCommand):
    help = 'Seed database with test data including mock trips and reviews'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Cleaning old data..."))

        Review.objects.all().delete()
        Trip.objects.all().delete()
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

        self.stdout.write(self.style.SUCCESS("Creating roles..."))
        customer_role = Role.objects.create(code="customer")
        driver_role = Role.objects.create(code="driver")
        admin_role = Role.objects.create(code="admin")

        self.stdout.write(self.style.SUCCESS("Creating car types..."))
        economy = CarType.objects.create(code="economy", description="Доступные авто")
        comfort = CarType.objects.create(code="comfort", description="Комфорт класс")
        premium = CarType.objects.create(code="premium", description="Премиум авто")
        business = CarType.objects.create(code="business", description="Бизнес класс")

        self.stdout.write(self.style.SUCCESS("Creating tariffs..."))
        t1 = Tariff.objects.create(code="economy", base_price=600, price_per_km=90, price_per_min=15, min_price=600, is_active=True)
        t2 = Tariff.objects.create(code="comfort", base_price=900, price_per_km=120, price_per_min=20, min_price=900, is_active=True)
        t3 = Tariff.objects.create(code="premium", base_price=1800, price_per_km=200, price_per_min=35, min_price=1800, is_active=True)
        t4 = Tariff.objects.create(code="business", base_price=3000, price_per_km=250, price_per_min=45, min_price=3000, is_active=True)

        CarTypeTariff.objects.create(car_type=economy, tariff=t1)
        CarTypeTariff.objects.create(car_type=comfort, tariff=t2)
        CarTypeTariff.objects.create(car_type=premium, tariff=t3)
        CarTypeTariff.objects.create(car_type=business, tariff=t4)

        self.stdout.write(self.style.SUCCESS("Creating car brands..."))
        brand_objects = []
        for name, manufacturer in [
            ("Chevrolet Cobalt", "Chevrolet"),
            ("Lada Granta", "Lada"),
            ("Toyota Camry", "Toyota"),
            ("Hyundai Sonata", "Hyundai"),
            ("Kia K5", "Kia"),
        ]:
            brand_objects.append(CarBrand.objects.create(name=name, manufacturer=manufacturer))

        self.stdout.write(self.style.SUCCESS("Creating admin user..."))
        admin_user = User.objects.create_user(
            phone="+77000000000",
            password="admin1234",
            first_name="Admin",
            last_name="Test",
            is_verified=True,
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        UserRole.objects.create(user=admin_user, role=admin_role)

        self.stdout.write(self.style.SUCCESS("Creating customers..."))
        customers = []
        for i in range(1, 11):
            user = User.objects.create_user(
                phone=f"+770100000{i:02d}",
                password="test1234",
                first_name=f"Customer{i}",
                last_name="Test",
                is_verified=True,
                is_active=True,
            )
            UserRole.objects.create(user=user, role=customer_role)
            customers.append(user)

        self.stdout.write(self.style.SUCCESS("Creating drivers..."))
        drivers = []
        for i in range(1, 31):
            user = User.objects.create_user(
                phone=f"+7702000000{i}",
                password="test1234",
                first_name=f"Driver{i}",
                last_name="Test",
                is_verified=True,
                is_active=True,
                is_staff=True,
            )
            UserRole.objects.create(user=user, role=driver_role)
            DriverProfile.objects.create(
                user=user,
                license_number=f"KZ-ALM-{100000 + i}",
                experience_years=3 + i % 7,
                rating_avg=Decimal("4.5") + Decimal(i) / Decimal("100"),
            )
            drivers.append(user)

        self.stdout.write(self.style.SUCCESS("Creating cars with locations..."))
        cars = []
        for idx, driver in enumerate(drivers):
            car = Car.objects.create(
                driver=driver,
                brand=brand_objects[idx % len(brand_objects)],
                car_type=[economy, comfort, premium, business][idx % 4],
                year=2020 + (idx % 5),
                plate_number=f"{100 + idx}ALA02",
                is_active=True,
            )
            cars.append(car)

            lat, lng, street_name = ASTANA_LOCATIONS[idx]
            CarLocation.objects.create(
                car=car,
                lat=lat,
                lng=lng,
                location=Point(lng, lat),
                speed_kmh=0,
                heading=0,
            )
            self.stdout.write(f"  Driver {idx + 1}: {street_name} ({lat}, {lng})")

        # ── Mock trips ────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("Creating mock trips and reviews..."))
        now = timezone.now()
        mt = lambda *a, **kw: _make_trip(now, *a, **kw)

        # Customer1 (+77010000001): 5 trips — 2 reviewed, 2 unreviewed, 1 cancelled
        t_c1_1 = mt(customers[0], drivers[0], cars[0], t1, 0, 14)
        t_c1_2 = mt(customers[0], drivers[1], cars[1], t2, 1, 10)
        t_c1_3 = mt(customers[0], drivers[2], cars[2], t1, 2, 7)   # no review
        t_c1_4 = mt(customers[0], drivers[3], cars[3], t3, 3, 4)   # no review
        mt(customers[0], drivers[4], cars[4], t2, 4, 2, status='cancelled')

        Review.objects.create(trip=t_c1_1, reviewer=customers[0], reviewed=drivers[0],
                              rating=5, comment="Excellent driver, very smooth ride!")
        Review.objects.create(trip=t_c1_2, reviewer=customers[0], reviewed=drivers[1],
                              rating=4, comment="")

        # Customer2 (+77010000002): 4 trips — 1 reviewed, 2 unreviewed, 1 cancelled
        t_c2_1 = mt(customers[1], drivers[0], cars[0], t2, 5, 12)
        mt(customers[1], drivers[2], cars[2], t1, 6, 8)             # no review
        mt(customers[1], drivers[4], cars[4], t3, 7, 5)             # no review
        mt(customers[1], drivers[1], cars[1], t4, 8, 1, status='cancelled')

        Review.objects.create(trip=t_c2_1, reviewer=customers[1], reviewed=drivers[0],
                              rating=3, comment="Average experience, took a longer route.")

        # Customer3 (+77010000003): 2 completed, no reviews
        mt(customers[2], drivers[3], cars[3], t1, 9, 6)
        mt(customers[2], drivers[1], cars[1], t2, 10, 3)

        # Customer4 (+77010000004): 2 trips — 1 reviewed, 1 unreviewed
        t_c4_1 = mt(customers[3], drivers[4], cars[4], t4, 11, 9)
        mt(customers[3], drivers[0], cars[0], t3, 0, 1)             # no review

        Review.objects.create(trip=t_c4_1, reviewer=customers[3], reviewed=drivers[4],
                              rating=5, comment="Amazing premium experience!")

        # ── Summary ──────────────────────────────────────────────────────────
        completed = Trip.objects.filter(status='completed').count()
        cancelled = Trip.objects.filter(status='cancelled').count()
        reviewed = Review.objects.count()

        self.stdout.write(self.style.SUCCESS("\n=== SEED COMPLETED SUCCESSFULLY ==="))
        self.stdout.write(f"Admins:    {UserRole.objects.filter(role=admin_role).count()}")
        self.stdout.write(f"Customers: {UserRole.objects.filter(role=customer_role).count()}")
        self.stdout.write(f"Drivers:   {UserRole.objects.filter(role=driver_role).count()}")
        self.stdout.write(f"Trips:     {Trip.objects.count()} ({completed} completed, {cancelled} cancelled)")
        self.stdout.write(f"Reviews:   {reviewed} submitted, {completed - reviewed} awaiting rating")
        self.stdout.write(self.style.SUCCESS("\nTest accounts:"))
        self.stdout.write("  Admin:     +77000000000  (password: admin1234)")
        self.stdout.write("  Customers: +77010000001 to +77010000010  (password: test1234)")
        self.stdout.write("  Drivers:   +77020000001 to +77020000030  (password: test1234)")
        self.stdout.write(self.style.SUCCESS("\nMock trip data:"))
        self.stdout.write("  +77010000001 — 5 trips: 2 reviewed, 2 pending review, 1 cancelled")
        self.stdout.write("  +77010000002 — 4 trips: 1 reviewed, 2 pending review, 1 cancelled")
        self.stdout.write("  +77010000003 — 2 trips: both pending review (no reviews at all)")
        self.stdout.write("  +77010000004 — 2 trips: 1 reviewed, 1 pending review")
