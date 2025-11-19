from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime, timedelta
from .models import Resource
from django.contrib.auth import get_user_model

User = get_user_model()


class ResourceAPITestCase(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Создаем пользователей без username
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123'
        )

        self.resource = Resource.objects.create(
            name="API Тестовый ресурс",
            location="API Тестовое место",
            capacity=20,
            is_active=True
        )

        self.tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    def test_get_resources_list(self):
        """Тест получения списка ресурсов"""
        response = self.client.get('/api/resources/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_get_resource_detail(self):
        """Тест получения деталей ресурса"""
        response = self.client.get(f'/api/resources/{self.resource.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.resource.name)
        self.assertEqual(response.data['location'], self.resource.location)

    def test_get_resource_availability(self):
        """Тест получения доступности ресурса"""
        response = self.client.get(
            f'/api/resources/{self.resource.id}/availability?date={self.tomorrow}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('slots', response.data)
        self.assertIn('available_slots', response.data)
        self.assertIn('total_slots', response.data)

    def test_get_resource_availability_no_date(self):
        """Тест получения доступности без даты"""
        response = self.client.get(f'/api/resources/{self.resource.id}/availability')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_resource_availability_invalid_date(self):
        """Тест получения доступности с неверной датой"""
        response = self.client.get(
            f'/api/resources/{self.resource.id}/availability?date=invalid-date'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)