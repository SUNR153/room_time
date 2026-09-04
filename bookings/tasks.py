from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from resources.services import AvailabilityService

from .models import Booking


@shared_task
def expire_stale_holds():
    """
    Периодическая задача: отменяет holds (pending-бронирования), которые
    не были подтверждены в течение bookings.views.HOLD_EXPIRY_MINUTES.
    """
    from .views import HOLD_EXPIRY_MINUTES

    cutoff = timezone.now() - timedelta(minutes=HOLD_EXPIRY_MINUTES)
    stale_bookings = Booking.objects.filter(status='pending', created_at__lt=cutoff)

    expired_count = 0
    for booking in stale_bookings:
        booking.status = 'cancelled'
        booking.save(update_fields=['status'])
        AvailabilityService.handle_booking_change(booking)
        expired_count += 1

    return expired_count
