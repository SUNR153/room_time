from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Notification

User = get_user_model()


class NotificationModelTests(TestCase):
    def test_str_truncates_message(self):
        user = User.objects.create_user(email='alice@example.com', password='pass12345')
        notification = Notification.objects.create(
            user=user,
            message='This is a fairly long notification message that should be truncated',
        )
        self.assertTrue(str(notification).startswith('alice@example.com - '))

    def test_default_unread(self):
        user = User.objects.create_user(email='bob@example.com', password='pass12345')
        notification = Notification.objects.create(user=user, message='Hi')
        self.assertFalse(notification.is_read)


class NotificationViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='alice@example.com', password='pass12345')
        self.other_user = User.objects.create_user(email='bob@example.com', password='pass12345')

    def test_list_requires_authentication(self):
        response = self.client.get(reverse('notifications:list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_only_returns_own_notifications(self):
        Notification.objects.create(user=self.user, message='Mine')
        Notification.objects.create(user=self.other_user, message='Not mine')

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('notifications:list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['message'], 'Mine')

    def test_mark_read(self):
        notification = Notification.objects.create(user=self.user, message='Hi')
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('notifications:mark_read', args=[notification.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_read_returns_404_for_other_users_notification(self):
        notification = Notification.objects.create(user=self.other_user, message='Hi')
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('notifications:mark_read', args=[notification.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_all_read(self):
        Notification.objects.create(user=self.user, message='One')
        Notification.objects.create(user=self.user, message='Two')
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('notifications:mark_all_read'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['marked_read'], 2)
        self.assertEqual(self.user.notifications.filter(is_read=False).count(), 0)
