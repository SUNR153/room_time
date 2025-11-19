from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from .models import Resource
from .services import AvailabilityService
from .cache import AvailabilityCache

User = get_user_model()


class AvailabilityCacheTestCase(TestCase):

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.resource = Resource.objects.create(
            name="Тестовый ресурс",
            location="Тестовое место",
            capacity=10,
            is_active=True
        )

        self.date = datetime.now().date() + timedelta(days=1)

    def test_availability_cache_set_get(self):
        """Тест сохранения и получения из кеша"""
        test_data = {
            "resource_id": str(self.resource.id),
            "date": self.date.isoformat(),
            "slots": [],
            "available_slots": 0,
            "total_slots": 0,
            "calculated_at": datetime.now().isoformat()
        }

        # Сохраняем в кеш
        AvailabilityCache.set_availability(self.resource.id, self.date, test_data)

        # Получаем из кеша
        cached_data = AvailabilityCache.get_availability(self.resource.id, self.date)

        self.assertEqual(cached_data, test_data)

    def test_availability_cache_invalidation(self):
        """Тест инвалидации кеша"""
        test_data = {"test": "data"}

        # Сохраняем в кеш
        AvailabilityCache.set_availability(self.resource.id, self.date, test_data)

        # Проверяем, что данные есть в кеше
        cached_data_before = AvailabilityCache.get_availability(self.resource.id, self.date)
        self.assertEqual(cached_data_before, test_data)

        # Инвалидируем
        AvailabilityCache.invalidate_resource_availability(self.resource.id)

        # Проверяем, что данные удалены
        cached_data_after = AvailabilityCache.get_availability(self.resource.id, self.date)
        self.assertIsNone(cached_data_after)

    def test_availability_service_calculation(self):
        """Тест вычисления доступности"""
        availability_data = AvailabilityService.get_resource_availability(
            self.resource.id, self.date
        )

        self.assertIn('resource_id', availability_data)
        self.assertIn('slots', availability_data)
        self.assertIn('available_slots', availability_data)
        self.assertIn('total_slots', availability_data)
        self.assertEqual(availability_data['resource_id'], str(self.resource.id))
        self.assertEqual(availability_data['date'], self.date.isoformat())


class ResourceModelTestCase(TestCase):

    def setUp(self):
        self.resource = Resource.objects.create(
            name="Тестовый ресурс",
            location="Тестовое место",
            capacity=15,
            is_active=True
        )

    def test_resource_creation(self):
        """Тест создания ресурса"""
        self.assertEqual(self.resource.name, "Тестовый ресурс")
        self.assertEqual(self.resource.location, "Тестовое место")
        self.assertEqual(self.resource.capacity, 15)
        self.assertTrue(self.resource.is_active)
        self.assertIsNotNone(self.resource.created_at)

    def test_resource_str_method(self):
        """Тест строкового представления ресурса"""
        expected_str = f"{self.resource.name} ({self.resource.location}) - Активен"
        self.assertEqual(str(self.resource), expected_str)

    def test_resource_has_file_property(self):
        """Тест свойства has_file"""
        self.assertFalse(self.resource.has_file)


class CacheStatsTestCase(TestCase):

    def test_cache_stats(self):
        """Тест получения статистики кеша"""
        stats = AvailabilityCache.get_availability_stats()

        self.assertIn('total_cached_dates', stats)
        self.assertIn('resources', stats)
        self.assertIsInstance(stats['total_cached_dates'], int)
        self.assertIsInstance(stats['resources'], dict)