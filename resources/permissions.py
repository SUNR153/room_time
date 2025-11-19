from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Разрешение только для администраторов
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'

class IsAuthenticated(permissions.BasePermission):
    """
    Разрешение для всех аутентифицированных пользователей
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated