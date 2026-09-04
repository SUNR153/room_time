from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from bookings.models import Booking
from resources.models import Resource

from .models import Payment

User = get_user_model()


class PaymentFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='pass12345')
        self.other_user = User.objects.create_user(email='other@example.com', password='pass12345')
        self.resource = Resource.objects.create(
            name='Meeting Room A',
            location='2nd floor',
            capacity=6,
            price_per_hour=Decimal('20.00'),
            is_active=True,
        )
        self.booking = Booking.objects.create(
            user=self.user,
            resource=self.resource,
            starts_at=timezone.now() + timedelta(hours=2),
            ends_at=timezone.now() + timedelta(hours=4),
            status='confirmed',
        )

    def test_pay_requires_authentication(self):
        response = self.client.post(reverse('payments:pay'), {'booking_id': self.booking.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pay_computes_amount_from_duration_and_price(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('payments:pay'), {'booking_id': self.booking.id, 'method': 'card'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # 2 hours * 20.00/hour
        self.assertEqual(Decimal(response.data['amount']), Decimal('40.00'))
        self.assertEqual(response.data['status'], 'paid')

    def test_pay_forbidden_for_non_owner(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(reverse('payments:pay'), {'booking_id': self.booking.id})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_pay_for_pending_booking(self):
        self.booking.status = 'pending'
        self.booking.save(update_fields=['status'])

        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('payments:pay'), {'booking_id': self.booking.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_pay_twice(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(reverse('payments:pay'), {'booking_id': self.booking.id})
        response = self.client.post(reverse('payments:pay'), {'booking_id': self.booking.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Payment.objects.filter(booking=self.booking).count(), 1)

    def test_my_payments_only_returns_own(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(reverse('payments:pay'), {'booking_id': self.booking.id})

        response = self.client.get(reverse('payments:mine'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse('payments:mine'))
        self.assertEqual(len(response.data), 0)

    def test_payment_detail_forbidden_for_non_owner(self):
        self.client.force_authenticate(user=self.user)
        pay_response = self.client.post(reverse('payments:pay'), {'booking_id': self.booking.id})
        payment_id = pay_response.data['id']

        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse('payments:detail', args=[payment_id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
