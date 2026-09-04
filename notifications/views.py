from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(APIView):
    """
    GET /api/notifications/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = request.user.notifications.all()
        return Response(NotificationSerializer(notifications, many=True).data)


class NotificationMarkReadView(APIView):
    """
    POST /api/notifications/<id>/read/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    """
    POST /api/notifications/read_all/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = request.user.notifications.filter(is_read=False).update(is_read=True)
        return Response({'marked_read': updated}, status=status.HTTP_200_OK)
