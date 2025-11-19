from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class AvailabilityCache:
    """
    Класс для работы с кешем доступности ресурсов
    """

    # Префикс для ключей кеша доступности
    AVAILABILITY_KEY_PREFIX = 'avail'

    # TTL кеша в секундах (30-120 секунд как в ТЗ)
    DEFAULT_TTL = 60

    # Префикс для ключей инвалидации
    INVALIDATION_KEY_PREFIX = 'avail_invalid'

    @classmethod
    def get_availability_key(cls, resource_id, date):
        """
        Генерирует ключ для кеша доступности ресурса на конкретную дату
        :param resource_id: UUID ресурса
        :param date: дата в формате YYYY-MM-DD или datetime.date
        :return: строковый ключ
        """
        if isinstance(date, datetime):
            date_str = date.strftime('%Y-%m-%d')
        else:
            date_str = str(date)

        return f"{cls.AVAILABILITY_KEY_PREFIX}:{resource_id}:{date_str}"

    @classmethod
    def get_invalidation_key(cls, resource_id):
        """
        Генерирует ключ для отслеживания инвалидации ресурса
        :param resource_id: UUID ресурса
        :return: строковый ключ
        """
        return f"{cls.INVALIDATION_KEY_PREFIX}:{resource_id}"

    @classmethod
    def set_availability(cls, resource_id, date, availability_data, ttl=None):
        """
        Сохраняет данные о доступности в кеш
        :param resource_id: UUID ресурса
        :param date: дата
        :param availability_data: данные о доступности
        :param ttl: время жизни в секундах
        """
        if ttl is None:
            ttl = cls.DEFAULT_TTL

        key = cls.get_availability_key(resource_id, date)

        try:
            cache.set(key, availability_data, timeout=ttl)
            logger.debug(f"Кеш доступности сохранен: {key}, TTL: {ttl}с")
        except Exception as e:
            logger.error(f"Ошибка сохранения кеша доступности {key}: {str(e)}")

    @classmethod
    def get_availability(cls, resource_id, date):
        """
        Получает данные о доступности из кеша
        :param resource_id: UUID ресурса
        :param date: дата
        :return: данные о доступности или None
        """
        key = cls.get_availability_key(resource_id, date)

        try:
            data = cache.get(key)
            if data is not None:
                logger.debug(f"Кеш доступности получен: {key}")
            return data
        except Exception as e:
            logger.error(f"Ошибка получения кеша доступности {key}: {str(e)}")
            return None

    @classmethod
    def invalidate_resource_availability(cls, resource_id, dates=None):
        """
        Инвалидирует кеш доступности для ресурса
        :param resource_id: UUID ресурса
        :param dates: конкретные даты для инвалидации (опционально)
        """
        try:
            if dates:
                # Инвалидируем только указанные даты
                for date in dates:
                    key = cls.get_availability_key(resource_id, date)
                    cache.delete(key)
                    logger.debug(f"Кеш доступности инвалидирован: {key}")
            else:
                # Инвалидируем все даты для ресурса
                # Используем шаблон для поиска всех ключей ресурса
                pattern = f"{cls.AVAILABILITY_KEY_PREFIX}:{resource_id}:*"
                cls._delete_keys_by_pattern(pattern)

                # Устанавливаем маркер инвалидации
                invalidation_key = cls.get_invalidation_key(resource_id)
                cache.set(invalidation_key, timezone.now().isoformat(), timeout=3600)  # 1 час

                logger.debug(f"Весь кеш доступности инвалидирован для ресурса: {resource_id}")

        except Exception as e:
            logger.error(f"Ошибка инвалидации кеша для ресурса {resource_id}: {str(e)}")

    @classmethod
    def invalidate_multiple_resources(cls, resource_ids):
        """
        Инвалидирует кеш доступности для нескольких ресурсов
        :param resource_ids: список UUID ресурсов
        """
        for resource_id in resource_ids:
            cls.invalidate_resource_availability(resource_id)

    @classmethod
    def invalidate_all_availability(cls):
        """
        Инвалидирует весь кеш доступности (использовать осторожно!)
        """
        try:
            pattern = f"{cls.AVAILABILITY_KEY_PREFIX}:*"
            cls._delete_keys_by_pattern(pattern)
            logger.info("Весь кеш доступности инвалидирован")
        except Exception as e:
            logger.error(f"Ошибка полной инвалидации кеша доступности: {str(e)}")

    @classmethod
    def is_availability_invalidated(cls, resource_id):
        """
        Проверяет, был ли ресурс недавно инвалидирован
        :param resource_id: UUID ресурса
        :return: bool
        """
        invalidation_key = cls.get_invalidation_key(resource_id)
        return cache.get(invalidation_key) is not None

    @classmethod
    def clear_invalidation_marker(cls, resource_id):
        """
        Очищает маркер инвалидации для ресурса
        :param resource_id: UUID ресурса
        """
        invalidation_key = cls.get_invalidation_key(resource_id)
        cache.delete(invalidation_key)

    @classmethod
    def get_availability_stats(cls):
        """
        Возвращает статистику по кешу доступности
        :return: словарь со статистикой
        """
        try:
            pattern = f"{cls.AVAILABILITY_KEY_PREFIX}:*"
            keys = cls._get_keys_by_pattern(pattern)

            stats = {
                'total_cached_dates': len(keys),
                'resources': {}
            }

            # Группируем по ресурсам
            for key in keys:
                parts = key.split(':')
                if len(parts) >= 3:
                    resource_id = parts[1]
                    if resource_id not in stats['resources']:
                        stats['resources'][resource_id] = 0
                    stats['resources'][resource_id] += 1

            return stats

        except Exception as e:
            logger.error(f"Ошибка получения статистики кеша: {str(e)}")
            return {'error': str(e)}

    @classmethod
    def _delete_keys_by_pattern(cls, pattern):
        """
        Удаляет ключи по шаблону (для Redis)
        """
        try:
            # Для django-redis
            keys = cache.keys(pattern)
            if keys:
                cache.delete_many(keys)
                logger.debug(f"Удалено ключей по шаблону {pattern}: {len(keys)}")
        except Exception as e:
            logger.error(f"Ошибка удаления ключей по шаблону {pattern}: {str(e)}")

    @classmethod
    def _get_keys_by_pattern(cls, pattern):
        """
        Получает ключи по шаблону (для Redis)
        """
        try:
            return cache.keys(pattern) or []
        except Exception as e:
            logger.error(f"Ошибка получения ключей по шаблону {pattern}: {str(e)}")
            return []