from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('payments/pay/', views.PaymentCreateView.as_view(), name='pay'),
    path('payments/mine/', views.MyPaymentsView.as_view(), name='mine'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='detail'),
]
