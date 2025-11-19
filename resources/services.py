from django.utils import timezone
from datetime import datetime, timedelta
from .cache import AvailabilityCache
from .models import Resource, TimeSlot
import logging

logger = logging.getLogger(__name__)


class AvailabilityService:
    """
    Сервис для работы с доступностью ресурсов
    """

    @classmethod
    def get_resource_availability(cls, resource_id, date):
        """
        Получает доступность ресурса на дату (с использованием кеша)
        :param resource_id: UUID ресурса
        :param date: дата
        :return: данные о доступности
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
        :param resource_id: UUID ресурса
        :param date: дата
        :return: данные о доступности
        """
        try:
            # Получаем все слоты для ресурса на указанную дату
            start_of_day = datetime.combine(date, datetime.min.time())
            end_of_day = datetime.combine(date, datetime.max.time())

            slots = TimeSlot.objects.filter(
                resource_id=resource_id,
                starts_at__gte=start_of_day,
                ends_at__lte=end_of_day
            ).order_by('starts_at')

            # Формируем данные о доступности
            availability_data = {
                'resource_id': str(resource_id),
                'date': date.isoformat(),
                'slots': [],
                'available_slots': 0,
                'total_slots': slots.count(),
                'calculated_at': timezone.now().isoformat()
            }

            for slot in slots:
                slot_data = {
                    'id': str(slot.id),
                    'starts_at': slot.starts_at.isoformat(),
                    'ends_at': slot.ends_at.isoformat(),
                    'status': slot.status,
                    'is_available': slot.status == 'available'
                }
                availability_data['slots'].append(slot_data)

                if slot.status == 'available':
                    availability_data['available_slots'] += 1

            return availability_data

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
    def handle_resource_change(cls, resource_id, affected_dates=None):
        """
        Обрабатывает изменение ресурса (инвалидация кеша)
        :param resource_id: UUID ресурса
        :param affected_dates: затронутые даты (опционально)
        """
        logger.info(f"Инвалидация кеша для измененного ресурса: {resource_id}")
        AvailabilityCache.invalidate_resource_availability(resource_id, affected_dates)

    @classmethod
    def handle_slot_change(cls, slot):
        """
        Обрабатывает изменение слота (инвалидация кеша)
        :param slot: объект TimeSlot
        """
        resource_id = slot.resource_id
        slot_date = slot.starts_at.date()

        logger.info(f"Инвалидация кеша для измененного слота ресурса: {resource_id}, дата: {slot_date}")
        AvailabilityCache.invalidate_resource_availability(resource_id, [slot_date])

    @classmethod
    def handle_booking_change(cls, booking):
        """
        Обрабатывает изменение бронирования (инвалидация кеша)
        :param booking: объект Booking
        """
        resource_id = booking.resource_id
        # Инвалидируем все даты, затронутые бронированием
        start_date = booking.starts_at.date()
        end_date = booking.ends_at.date()

        affected_dates = []
        current_date = start_date
        while current_date <= end_date:
            affected_dates.append(current_date)
            current_date += timedelta(days=1)

        logger.info(f"Инвалидация кеша для измененного бронирования ресурса: {resource_id}, даты: {affected_dates}")
        AvailabilityCache.invalidate_resource_availability(resource_id, affected_dates)