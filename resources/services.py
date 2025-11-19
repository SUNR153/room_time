from django.utils import timezone
from datetime import datetime, timedelta
from .cache import AvailabilityCache
from .models import Resource
from django.contrib.auth import get_user_model
import logging
from bookings.models import Booking

logger = logging.getLogger(__name__)

User = get_user_model()

# Импортируем Booking из правильного приложения
try:
    from bookings.models import Booking
except ImportError:
    # Если приложение bookings не существует, создаем заглушку
    Booking = None
    logger.warning("Booking model not found. Availability will be calculated without bookings.")


class AvailabilityService:
    """
    Сервис для работы с доступностью ресурсов
    """

    # Длительность слота по умолчанию (в минутах)
    DEFAULT_SLOT_DURATION = 60  # 1 час

    @classmethod
    def get_resource_availability(cls, resource_id, date):
        """
        Получает доступность ресурса на дату (с использованием кеша)
        """
        # Пробуем получить из кеша
        cached_data = AvailabilityCache.get_availability(resource_id, date)
        if cached_data is not None:
            logger.debug(f"Данные получены из кеша для ресурса {resource_id} на {date}")
            return cached_data

        # Если нет в кеше, вычисляем и сохраняем
        availability_data = cls._calculate_availability(resource_id, date)

        # Сохраняем в кеш
        AvailabilityCache.set_availability(resource_id, date, availability_data)

        logger.debug(f"Данные вычислены и сохранены в кеш для ресурса {resource_id} на {date}")
        return availability_data

    @classmethod
    def _calculate_availability(cls, resource_id, date):
        """
        Вычисляет доступность ресурса на дату
        """
        try:
            # Получаем ресурс
            resource = Resource.objects.get(id=resource_id, is_active=True)

            # Получаем бронирования, если модель Booking доступна
            bookings = []
            if Booking:
                start_of_day = datetime.combine(date, datetime.min.time())
                end_of_day = datetime.combine(date, datetime.max.time())

                bookings = Booking.objects.filter(
                    resource_id=resource_id,
                    starts_at__lt=end_of_day,
                    ends_at__gt=start_of_day,
                    status__in=['confirmed', 'pending']
                ).order_by('starts_at')

            # Генерируем слоты на день
            slots = cls._generate_time_slots(date)

            # Отмечаем занятые слоты (если есть бронирования)
            available_slots = []
            for slot_start, slot_end in slots:
                is_available = True
                if bookings:
                    is_available = cls._is_slot_available(slot_start, slot_end, bookings)

                slot_data = {
                    'starts_at': slot_start.isoformat(),
                    'ends_at': slot_end.isoformat(),
                    'status': 'available' if is_available else 'booked',
                    'is_available': is_available
                }
                available_slots.append(slot_data)

            # Формируем данные о доступности
            availability_data = {
                'resource_id': str(resource_id),
                'resource_name': resource.name,
                'date': date.isoformat(),
                'slots': available_slots,
                'available_slots': len([s for s in available_slots if s['is_available']]),
                'total_slots': len(available_slots),
                'calculated_at': timezone.now().isoformat()
            }

            return availability_data

        except Resource.DoesNotExist:
            logger.error(f"Ресурс не найден или неактивен: {resource_id}")
            return {
                'resource_id': str(resource_id),
                'date': date.isoformat(),
                'slots': [],
                'available_slots': 0,
                'total_slots': 0,
                'error': 'Ресурс не найден или неактивен',
                'calculated_at': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Ошибка вычисления доступности для ресурса {resource_id} на {date}: {str(e)}")
            return {
                'resource_id': str(resource_id),
                'date': date.isoformat(),
                'slots': [],
                'available_slots': 0,
                'total_slots': 0,
                'error': str(e),
                'calculated_at': timezone.now().isoformat()
            }

    @classmethod
    def _generate_time_slots(cls, date, start_hour=8, end_hour=20, slot_duration=None):
        """
        Генерирует временные слоты на день
        """
        if slot_duration is None:
            slot_duration = cls.DEFAULT_SLOT_DURATION

        slots = []
        current_time = datetime.combine(date, datetime.min.time().replace(hour=start_hour))
        end_time = datetime.combine(date, datetime.min.time().replace(hour=end_hour))

        while current_time < end_time:
            slot_end = current_time + timedelta(minutes=slot_duration)
            if slot_end > end_time:
                break

            slots.append((current_time, slot_end))
            current_time = slot_end

        return slots

    @classmethod
    def _is_slot_available(cls, slot_start, slot_end, bookings):
        """
        Проверяет, доступен ли слот для бронирования
        """
        for booking in bookings:
            # Проверяем пересечение временных интервалов
            if (slot_start < booking.ends_at and slot_end > booking.starts_at):
                return False
        return True

    @classmethod
    def handle_resource_change(cls, resource_id, affected_dates=None):
        """
        Обрабатывает изменение ресурса (инвалидация кеша)
        """
        logger.info(f"Инвалидация кеша для измененного ресурса: {resource_id}")
        AvailabilityCache.invalidate_resource_availability(resource_id, affected_dates)

    @classmethod
    def handle_booking_change(cls, booking, old_dates=None):
        """
        Обрабатывает изменение бронирования (инвалидация кеша)
        """
        if not Booking:
            return  # Если Booking не доступен, пропускаем

        resource_id = booking.resource_id

        # Определяем затронутые даты
        affected_dates = set()

        # Добавляем даты из нового бронирования
        start_date = booking.starts_at.date()
        end_date = booking.ends_at.date()

        current_date = start_date
        while current_date <= end_date:
            affected_dates.add(current_date)
            current_date += timedelta(days=1)

        # Добавляем старые даты (если бронирование обновляется)
        if old_dates:
            for old_date in old_dates:
                affected_dates.add(old_date)

        logger.info(
            f"Инвалидация кеша для измененного бронирования ресурса: {resource_id}, даты: {list(affected_dates)}")
        AvailabilityCache.invalidate_resource_availability(resource_id, list(affected_dates))

    @classmethod
    def get_affected_dates_from_booking(cls, booking):
        """
        Получает список дат, затронутых бронированием
        """
        if not booking:
            return []

        start_date = booking.starts_at.date()
        end_date = booking.ends_at.date()

        affected_dates = []
        current_date = start_date
        while current_date <= end_date:
            affected_dates.append(current_date)
            current_date += timedelta(days=1)

        return affected_dates