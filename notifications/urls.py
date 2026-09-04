from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('notifications/', views.NotificationListView.as_view(), name='list'),
    path('notifications/<int:pk>/read/', views.NotificationMarkReadView.as_view(), name='mark_read'),
    path('notifications/read_all/', views.NotificationMarkAllReadView.as_view(), name='mark_all_read'),
]
