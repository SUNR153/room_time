from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Resource, TimeSlot, Booking
from .services import AvailabilityService
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Resource)
@receiver(post_delete, sender=Resource)
def on_resource_change(sender, instance, **kwargs):
    """
    Обработчик изменений ресурса
    """
    AvailabilityService.handle_resource_change(instance.id)

@receiver(post_save, sender=TimeSlot)
@receiver(post_delete, sender=TimeSlot)
def on_slot_change(sender, instance, **kwargs):
    """
    Обработчик изменений слота
    """
    AvailabilityService.handle_slot_change(instance)

@receiver(post_save, sender=Booking)
@receiver(post_delete, sender=Booking)
def on_booking_change(sender, instance, **kwargs):
    """
    Обработчик изменений бронирования
    """
    AvailabilityService.handle_booking_change(instance)

# Альтернативно: можно использовать более специфичные сигналы для статусов
@receiver(post_save, sender=Booking)
def on_booking_status_change(sender, instance, created, **kwargs):
    """
    Обработчик изменения статуса бронирования
    """
    if not created:
        # Проверяем, изменился ли статус
        if instance.tracker.has_changed('status'):
            AvailabilityService.handle_booking_change(instance)