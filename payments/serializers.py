from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'booking', 'amount', 'status', 'method', 'transaction_id', 'created_at', 'paid_at']
        read_only_fields = fields


class PaymentCreateSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField()
    method = serializers.ChoiceField(choices=Payment.METHOD_CHOICES, default='card')
