from rest_framework import serializers
from .models import TimeSlot, Booking


class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = '__all__'


class BookingHoldSerializer(serializers.Serializer):
    resource_id = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()


class BookingConfirmSerializer(serializers.Serializer):
    hold_key = serializers.CharField(max_length=255)


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['user', 'idempotency_key']