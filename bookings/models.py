from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

class TimeSlot(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('hold', 'Hold'),
        ('booked', 'Booked'),
    ]
    
    resource_id = models.IntegerField()
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['resource_id', 'starts_at', 'ends_at']
        indexes = [
            models.Index(fields=['resource_id', 'starts_at']),
            models.Index(fields=['status']),
        ]
    
    def clean(self):
        if self.starts_at >= self.ends_at:
            raise ValidationError('Start time must be before end time')
        if self.starts_at < timezone.now():
            raise ValidationError('Cannot create slot in the past')


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resource_id = models.IntegerField()
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['resource_id', 'starts_at']),
            models.Index(fields=['idempotency_key']),
        ]
    
    def clean(self):
        if self.starts_at >= self.ends_at:
            raise ValidationError('Start time must be before end time')
        if self.starts_at < timezone.now():
            raise ValidationError('Cannot book in the past')