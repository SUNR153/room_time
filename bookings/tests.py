from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from resources.models import Resource

from .models import Booking

User = get_user_model()


class BookingFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='pass12345')
        self.other_user = User.objects.create_user(email='other@example.com', password='pass12345')
        self.resource = Resource.objects.create(
            name='Meeting Room A',
            location='2nd floor',
            capacity=6,
            is_active=True,
        )
        self.starts_at = timezone.now() + timedelta(hours=2)
        self.ends_at = self.starts_at + timedelta(hours=1)

    def hold(self, user, starts_at=None, ends_at=None):
        self.client.force_authenticate(user=user)
        response = self.client.post(reverse('bookings:hold'), {
            'resource_id': str(self.resource.id),
            'starts_at': (starts_at or self.starts_at).isoformat(),
            'ends_at': (ends_at or self.ends_at).isoformat(),
        }, format='json')
        return response

    def test_hold_requires_authentication(self):
        response = self.client.post(reverse('bookings:hold'), {
            'resource_id': str(self.resource.id),
            'starts_at': self.starts_at.isoformat(),
            'ends_at': self.ends_at.isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_hold_creates_pending_booking(self):
        response = self.hold(self.user)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('hold_key', response.data)

        booking = Booking.objects.get(id=response.data['booking_id'])
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.user, self.user)

    def test_hold_rejects_end_before_start(self):
        response = self.hold(self.user, starts_at=self.ends_at, ends_at=self.starts_at)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_hold_rejects_overlapping_slot(self):
        first = self.hold(self.user)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        # Overlapping window with a different user
        second = self.hold(
            self.other_user,
            starts_at=self.starts_at + timedelta(minutes=30),
            ends_at=self.ends_at + timedelta(minutes=30),
        )
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)

    def test_non_overlapping_slot_is_allowed(self):
        first = self.hold(self.user)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.hold(
            self.other_user,
            starts_at=self.ends_at,
            ends_at=self.ends_at + timedelta(hours=1),
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)

    def test_confirm_success(self):
        hold_response = self.hold(self.user)
        hold_key = hold_response.data['hold_key']

        response = self.client.post(reverse('bookings:confirm'), {'hold_key': hold_key}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'confirmed')

    def test_confirm_fails_for_another_users_hold(self):
        hold_response = self.hold(self.user)
        hold_key = hold_response.data['hold_key']

        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(reverse('bookings:confirm'), {'hold_key': hold_key}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_confirm_fails_for_expired_hold(self):
        hold_response = self.hold(self.user)
        booking = Booking.objects.get(id=hold_response.data['booking_id'])
        booking.created_at = timezone.now() - timedelta(minutes=20)
        booking.save(update_fields=['created_at'])

        response = self.client.post(
            reverse('bookings:confirm'),
            {'hold_key': hold_response.data['hold_key']},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')

    def test_cancel_by_owner(self):
        hold_response = self.hold(self.user)
        booking_id = hold_response.data['booking_id']

        response = self.client.post(reverse('bookings:cancel', args=[booking_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')

    def test_cancel_forbidden_for_non_owner(self):
        hold_response = self.hold(self.user)
        booking_id = hold_response.data['booking_id']

        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(reverse('bookings:cancel', args=[booking_id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancelling_frees_the_slot_for_others(self):
        hold_response = self.hold(self.user)
        booking_id = hold_response.data['booking_id']
        self.client.post(reverse('bookings:cancel', args=[booking_id]))

        second = self.hold(self.other_user)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)

    def test_my_bookings_only_returns_own_bookings(self):
        self.hold(self.user)
        self.hold(self.other_user, starts_at=self.ends_at, ends_at=self.ends_at + timedelta(hours=1))

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('bookings:mine'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_booking_detail_forbidden_for_non_owner(self):
        hold_response = self.hold(self.user)
        booking_id = hold_response.data['booking_id']

        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse('bookings:detail', args=[booking_id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
