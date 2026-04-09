# backend/taxi/tests.py
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from .models import (
    Role, UserRole, DriverProfile, CarBrand, CarType,
    Car, CarLocation, Tariff, CarTypeTariff, Trip, Review, Payment
)

User = get_user_model()


def create_trip(customer, driver=None, tariff=None, status='requested'):
    return Trip.objects.create(
        customer=customer,
        driver=driver,
        tariff=tariff or Tariff.objects.first(),
        car=Car.objects.filter(driver=driver).first() if driver else None,
        start_lat=43.2389,
        start_lng=76.8897,
        end_lat=43.2500,
        end_lng=76.9000,
        distance_km=2.5,
        price=200.00,
        status=status
    )


class BaseTestCase(APITestCase):
    def setUp(self):
        self.role_customer = Role.objects.get_or_create(code='customer')[0]
        self.role_driver = Role.objects.get_or_create(code='driver')[0]
        self.role_admin = Role.objects.get_or_create(code='admin')[0]

        self.customer = User.objects.create_user(phone='+77011111111', password='pass123')
        self.driver_user = User.objects.create_user(phone='+77012222222', password='pass123')
        self.admin = User.objects.create_user(phone='+77013333333', password='pass123')

        UserRole.objects.bulk_create([
            UserRole(user=self.customer, role=self.role_customer),
            UserRole(user=self.driver_user, role=self.role_driver),
            UserRole(user=self.admin, role=self.role_admin),
        ])

        self.driver_profile = DriverProfile.objects.create(
            user=self.driver_user,
            license_number='A1234567',
            experience_years=3
        )

        self.brand = CarBrand.objects.create(name='Toyota')
        self.car_type = CarType.objects.create(code='economy')
        self.car = Car.objects.create(
            driver=self.driver_user,
            brand=self.brand,
            car_type=self.car_type,
            year=2020,
            plate_number='A123BC',
            is_active=True
        )

        self.tariff = Tariff.objects.create(
            code='base',
            base_price=100,
            price_per_km=10,
            price_per_min=2,
            is_active=True
        )
        CarTypeTariff.objects.create(car_type=self.car_type, tariff=self.tariff)

        self.client = APIClient()

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)


class AuthTests(BaseTestCase):
    def test_register_customer(self):
        url = reverse('taxi_api:register')
        data = {
            'phone': '+77014444444',
            'password': 'secure123',
            'password2': 'secure123',
            'first_name': 'Test'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(phone='+77014444444').exists())

    def test_login_success(self):
        url = reverse('taxi_api:login')
        data = {'phone': '+77011111111', 'password': 'pass123'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_login_fail(self):
        url = reverse('taxi_api:login')
        data = {'phone': '+77011111111', 'password': 'wrong'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RoleAndPermissionTests(BaseTestCase):
    def test_admin_can_view_all_users(self):
        self.authenticate_as(self.admin)
        url = reverse('taxi_api:admin-user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 3)

    def test_customer_cannot_access_admin_endpoints(self):
        self.authenticate_as(self.customer)
        url = reverse('taxi_api:admin-user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TripTests(BaseTestCase):
    def test_customer_can_create_trip(self):
        self.authenticate_as(self.customer)
        url = reverse('taxi_api:trip-create')
        data = {
            'tariff_code': self.tariff.code,  # ✅ string code, NOT id
            'start_lat': 43.2389,
            'start_lng': 76.8897,
            'end_lat': 43.2500,
            'end_lng': 76.9000,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Trip.objects.count(), 1)

    def test_customer_cannot_create_second_active_trip(self):
        self.authenticate_as(self.customer)
        create_trip(self.customer, status='requested')
        url = reverse('taxi_api:trip-create')
        data = {
            'tariff': self.tariff.id,
            'start_lat': 43.2389,
            'start_lng': 76.8897,
            'end_lat': 43.2500,
            'end_lng': 76.9000,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_driver_can_accept_trip(self):
        trip = create_trip(self.customer, status='requested')
        point = Point(76.8897, 43.2389, srid=4326)
        CarLocation.objects.create(car=self.car, lat=43.2389, lng=76.8897, location=point)
        self.authenticate_as(self.driver_user)
        url = reverse('taxi_api:trip-detail', kwargs={'id': trip.id})
        data = {'status': 'accepted'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        trip.refresh_from_db()
        self.assertEqual(trip.status, 'accepted')
        self.assertEqual(trip.driver, self.driver_user)

    def test_only_participant_can_review_trip(self):
        trip = create_trip(self.customer, self.driver_user, status='completed')
        other = User.objects.create_user(phone='+77019999999', password='pass')
        UserRole.objects.create(user=other, role=self.role_customer)
        self.authenticate_as(other)
        url = reverse('taxi_api:review-create', kwargs={'id': trip.id})
        data = {'reviewed': self.customer.id, 'rating': 5}
        response = self.client.post(url, data)
        # ⚠️ Should be 403, but current implementation returns 400
        # Keep expecting 403 to enforce correct behavior
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LocationTests(BaseTestCase):
    def test_driver_can_update_location(self):
        self.authenticate_as(self.driver_user)
        url = reverse('taxi_api:update-location')
        data = {
            'car_id': self.car.id,
            'lat': 43.2389,
            'lng': 76.8897,
            'speed_kmh': 45.5,
            'heading': 90.0
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_customer_can_find_nearby_cars(self):
        point = Point(76.8897, 43.2389, srid=4326)
        CarLocation.objects.create(car=self.car, lat=43.2389, lng=76.8897, location=point)
        self.authenticate_as(self.customer)
        url = reverse('taxi_api:nearby-cars')
        params = {'lat': 43.2389, 'lng': 76.8897, 'radius': 1000, 'limit': 10}
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class DriverStatusTests(BaseTestCase):
    def test_driver_online_status_offline(self):
        # Make driver offline by deactivating the only car
        self.car.is_active = False
        self.car.save(update_fields=['is_active'])

        self.authenticate_as(self.driver_user)
        url = reverse('taxi_api:driver-online-status')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['online'], False)
        self.assertIsNone(response.data['active_car'])
        # No active car -> no location context
        self.assertTrue(response.data['location_is_stale'])

    def test_driver_online_status_online_fresh_location(self):
        point = Point(76.8897, 43.2389, srid=4326)
        CarLocation.objects.create(car=self.car, lat=43.2389, lng=76.8897, location=point)

        self.authenticate_as(self.driver_user)
        url = reverse('taxi_api:driver-online-status')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['online'], True)
        self.assertIsNotNone(response.data['active_car'])
        self.assertEqual(response.data['active_car']['id'], self.car.id)
        self.assertEqual(response.data['last_location']['lat'], 43.2389)
        self.assertEqual(response.data['last_location']['lng'], 76.8897)
        self.assertEqual(response.data['location_is_stale'], False)

    def test_driver_online_status_online_stale_location(self):
        point = Point(76.8897, 43.2389, srid=4326)
        loc = CarLocation.objects.create(car=self.car, lat=43.2389, lng=76.8897, location=point)
        # Force location to be stale
        CarLocation.objects.filter(id=loc.id).update(updated_at=timezone.now() - timezone.timedelta(minutes=10))

        self.authenticate_as(self.driver_user)
        url = reverse('taxi_api:driver-online-status')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['online'], True)
        self.assertTrue(response.data['location_is_stale'])

    def test_driver_dashboard_contains_expected_sections(self):
        point = Point(76.8897, 43.2389, srid=4326)
        CarLocation.objects.create(car=self.car, lat=43.2389, lng=76.8897, location=point)

        self.authenticate_as(self.driver_user)
        url = reverse('taxi_api:driver-dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('driver_profile', response.data)
        self.assertIn('cars', response.data)
        self.assertIn('online_status', response.data)
        self.assertIn('active_trip', response.data)
        self.assertTrue(response.data['online_status']['online'])

    def test_driver_earnings_summary(self):
        # Completed trips for driver
        trip1 = create_trip(self.customer, driver=self.driver_user, status='completed')
        trip1.price = 1000
        trip1.save(update_fields=['price'])
        trip2 = create_trip(self.customer, driver=self.driver_user, status='completed')
        trip2.price = 500
        trip2.save(update_fields=['price'])

        # Mark one payment as paid, other unpaid
        Payment.objects.create(trip=trip1, amount=trip1.price, method='card', status='paid')
        Payment.objects.create(trip=trip2, amount=trip2.price, method='cash', status='pending')

        self.authenticate_as(self.driver_user)
        url = reverse('taxi_api:driver-earnings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['trips_completed'], 2)
        self.assertEqual(response.data['gross'], 1500.0)
        self.assertEqual(response.data['paid'], 1000.0)
        self.assertEqual(response.data['unpaid'], 500.0)


class PaymentTests(BaseTestCase):
    def test_customer_can_create_payment_for_own_trip(self):
        trip = create_trip(self.customer, status='completed')
        self.authenticate_as(self.customer)
        url = reverse('taxi_api:payment-create')
        data = {'trip': str(trip.id), 'method': 'card'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_pay_for_other_user_trip(self):
        other_customer = User.objects.create_user(phone='+77015555555', password='pass')
        UserRole.objects.create(user=other_customer, role=self.role_customer)
        trip = create_trip(other_customer, status='completed')
        self.authenticate_as(self.customer)
        url = reverse('taxi_api:payment-create')
        data = {'trip': str(trip.id), 'method': 'cash'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)