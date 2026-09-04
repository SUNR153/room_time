import uuid
from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from resources.models import Resource
from resources.services import AvailabilityService

from .models import Booking
from .serializers import (
    BookingConfirmSerializer,
    BookingHoldSerializer,
    BookingSerializer,
)

# Сколько времени удержание (hold) остаётся действительным, если не подтверждено
HOLD_EXPIRY_MINUTES = 10


def _has_overlap(resource, starts_at, ends_at, exclude_pk=None):
    """
    Проверяет пересечение с активными (pending/confirmed) бронированиями того же ресурса.
    Просроченные незавершённые holds (pending старше HOLD_EXPIRY_MINUTES) не учитываются.
    """
    hold_cutoff = timezone.now() - timedelta(minutes=HOLD_EXPIRY_MINUTES)

    qs = Booking.objects.select_for_update().filter(
        resource=resource,
        starts_at__lt=ends_at,
        ends_at__gt=starts_at,
    ).exclude(
        status='cancelled',
    ).exclude(
        status='pending', created_at__lt=hold_cutoff,
    )

    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    return qs.exists()


class BookingHoldView(APIView):
    """
    POST /api/bookings/hold/
    Создаёт временное удержание слота (Booking со статусом pending).
    Клиент должен подтвердить его через /confirm/ в течение HOLD_EXPIRY_MINUTES,
    иначе слот освобождается автоматически (см. scheduler).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BookingHoldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resource_id = serializer.validated_data['resource_id']
        starts_at = serializer.validated_data['starts_at']
        ends_at = serializer.validated_data['ends_at']

        if starts_at >= ends_at:
            return Response(
                {'error': 'starts_at must be before ends_at'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if starts_at < timezone.now():
            return Response(
                {'error': 'Cannot book in the past'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resource = get_object_or_404(Resource, pk=resource_id, is_active=True)

        with transaction.atomic():
            if _has_overlap(resource, starts_at, ends_at):
                return Response(
                    {'error': 'This resource is not available for the selected time range'},
                    status=status.HTTP_409_CONFLICT,
                )

            booking = Booking.objects.create(
                user=request.user,
                resource=resource,
                starts_at=starts_at,
                ends_at=ends_at,
                status='pending',
                idempotency_key=str(uuid.uuid4()),
            )

        return Response(
            {
                'hold_key': booking.idempotency_key,
                'booking_id': booking.id,
                'expires_in_minutes': HOLD_EXPIRY_MINUTES,
            },
            status=status.HTTP_201_CREATED,
        )


class BookingConfirmView(APIView):
    """
    POST /api/bookings/confirm/
    Подтверждает ранее созданный hold (переводит Booking в status=confirmed).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BookingConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hold_key = serializer.validated_data['hold_key']

        booking = get_object_or_404(
            Booking,
            idempotency_key=hold_key,
            user=request.user,
            status='pending',
        )

        hold_cutoff = timezone.now() - timedelta(minutes=HOLD_EXPIRY_MINUTES)
        if booking.created_at < hold_cutoff:
            booking.status = 'cancelled'
            booking.save(update_fields=['status'])
            return Response(
                {'error': 'This hold has expired, please create a new one'},
                status=status.HTTP_410_GONE,
            )

        booking.status = 'confirmed'
        booking.save(update_fields=['status'])

        AvailabilityService.handle_booking_change(booking)

        return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)


class BookingCancelView(APIView):
    """
    POST /api/bookings/<id>/cancel/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)

        if booking.user != request.user:
            return Response(
                {'error': 'You do not have permission to cancel this booking'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if booking.status == 'cancelled':
            return Response(
                {'error': 'Booking is already cancelled'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = 'cancelled'
        booking.save(update_fields=['status'])

        AvailabilityService.handle_booking_change(booking)

        return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)


class MyBookingsView(APIView):
    """
    GET /api/bookings/mine/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
        return Response(BookingSerializer(bookings, many=True).data)


class BookingDetailView(APIView):
    """
    GET /api/bookings/<id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)

        if booking.user != request.user:
            return Response(
                {'error': 'You do not have permission to view this booking'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(BookingSerializer(booking).data)
