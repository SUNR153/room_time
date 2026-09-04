from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking
from notifications.models import Notification

from .models import Payment
from .serializers import PaymentCreateSerializer, PaymentSerializer


class PaymentCreateView(APIView):
    """
    POST /api/payments/pay/
    Оплачивает подтверждённое бронирование (мок платёжного шлюза —
    оплата проходит мгновенно и всегда успешно).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking = get_object_or_404(
            Booking,
            pk=serializer.validated_data['booking_id'],
            user=request.user,
        )

        if booking.status != 'confirmed':
            return Response(
                {'error': 'Only confirmed bookings can be paid for'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(booking, 'payment') and booking.payment.status == 'paid':
            return Response(
                {'error': 'This booking has already been paid for'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        duration_hours = Decimal((booking.ends_at - booking.starts_at).total_seconds()) / Decimal(3600)
        amount = duration_hours * booking.resource.price_per_hour

        payment, _created = Payment.objects.update_or_create(
            booking=booking,
            defaults={
                'amount': amount,
                'method': serializer.validated_data['method'],
                'status': 'paid',
                'paid_at': timezone.now(),
            },
        )

        Notification.objects.create(
            user=request.user,
            message=f"Payment of {amount} received for booking #{booking.id}.",
        )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class MyPaymentsView(APIView):
    """
    GET /api/payments/mine/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = Payment.objects.filter(booking__user=request.user).order_by('-created_at')
        return Response(PaymentSerializer(payments, many=True).data)


class PaymentDetailView(APIView):
    """
    GET /api/payments/<id>/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)

        if payment.booking.user != request.user:
            return Response(
                {'error': 'You do not have permission to view this payment'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(PaymentSerializer(payment).data)
