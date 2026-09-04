from django.urls import path

from . import views

app_name = 'bookings'

urlpatterns = [
    path('bookings/hold/', views.BookingHoldView.as_view(), name='hold'),
    path('bookings/confirm/', views.BookingConfirmView.as_view(), name='confirm'),
    path('bookings/mine/', views.MyBookingsView.as_view(), name='mine'),
    path('bookings/<int:pk>/', views.BookingDetailView.as_view(), name='detail'),
    path('bookings/<int:pk>/cancel/', views.BookingCancelView.as_view(), name='cancel'),
]
