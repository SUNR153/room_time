from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import Resource, Booking
from .services import AvailabilityService
import logging
from bookings.models import Booking

logger = logging.getLogger(__name__)

# Для отслеживания изменений в бронированиях
booking_old_dates = {}

@receiver(pre_save, sender=Booking)
def store_old_booking_dates(sender, instance, **kwargs):
    """
    Сохраняет старые даты бронирования перед обновлением
    """
    if instance.pk:
        try:
            old_booking = Booking.objects.get(pk=instance.pk)
            booking_old_dates[instance.pk] = AvailabilityService.get_affected_dates_from_booking(old_booking)
        except Booking.DoesNotExist:
            pass

@receiver(post_save, sender=Resource)
@receiver(post_delete, sender=Resource)
def on_resource_change(sender, instance, **kwargs):
    """
    Обработчик изменений ресурса
    """
    AvailabilityService.handle_resource_change(instance.id)

@receiver(post_save, sender=Booking)
def on_booking_save(sender, instance, created, **kwargs):
    """
    Обработчик сохранения бронирования
    """
    old_dates = booking_old_dates.pop(instance.pk, None) if not created else None
    AvailabilityService.handle_booking_change(instance, old_dates)

@receiver(post_delete, sender=Booking)
def on_booking_delete(sender, instance, **kwargs):
    """
    Обработчик удаления бронирования
    """
    AvailabilityService.handle_booking_change(instance)

# Дополнительные сигналы для конкретных изменений статуса
@receiver(post_save, sender=Booking)
def on_booking_status_change(sender, instance, created, **kwargs):
    """
    Обработчик изменения статуса бронирования
    """
    if not created:
        # Если статус изменился, инвалидируем кеш
        try:
            old_booking = Booking.objects.get(pk=instance.pk)
            if old_booking.status != instance.status:
                old_dates = AvailabilityService.get_affected_dates_from_booking(old_booking)
                AvailabilityService.handle_booking_change(instance, old_dates)
        except Booking.DoesNotExist:
            pass