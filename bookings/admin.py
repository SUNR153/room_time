from django.contrib import admin
from .models import TimeSlot, Booking


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['resource_id', 'starts_at', 'ends_at', 'status', 'created_at']
    list_filter = ['status', 'resource_id', 'created_at']
    search_fields = ['resource_id']
    ordering = ['-created_at']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'resource_id', 'starts_at', 'ends_at', 'status', 'created_at']
    list_filter = ['status', 'resource_id', 'created_at']
    search_fields = ['user__username', 'user__email', 'resource_id']
    ordering = ['-created_at']
    readonly_fields = ['idempotency_key', 'created_at', 'updated_at']