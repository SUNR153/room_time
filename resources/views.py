from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from datetime import datetime
from .services import AvailabilityService
from .cache import AvailabilityCache

from .models import Resource, FileUpload
from .serializers import (
    ResourceSerializer, ResourceCreateSerializer,
    ResourceUpdateSerializer, FileUploadSerializer
)
from .permissions import IsAdminUser
from .validators import FileValidator


class ResourceViewSet(viewsets.ViewSet):
    """
    ViewSet для управления ресурсами
    """

    def get_permissions(self):
        """
        Определение прав доступа в зависимости от действия
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'upload_file']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def list(self, request):
        """
        GET /resources - список всех активных ресурсов
        """
        cache_key = 'active_resources_list'
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        resources = Resource.objects.filter(is_active=True).order_by('-created_at')
        serializer = ResourceSerializer(
            resources,
            many=True,
            context={'request': request}
        )

        # Кешируем на 60 секунд
        cache.set(cache_key, serializer.data, 60)

        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """
        GET /resources/{id} - детали конкретного ресурса
        """
        cache_key = f'resource_detail_{pk}'
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        resource = get_object_or_404(Resource, pk=pk)

        # Проверяем, активен ли ресурс или пользователь - администратор
        if not resource.is_active and not (request.user.role == 'admin'):
            return Response(
                {'error': 'Ресурс не найден или неактивен'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ResourceSerializer(resource, context={'request': request})

        # Кешируем на 60 секунд
        cache.set(cache_key, serializer.data, 60)

        return Response(serializer.data)

    def create(self, request):
        """
        POST /resources - создание нового ресурса
        """
        serializer = ResourceCreateSerializer(data=request.data)
        if serializer.is_valid():
            resource = serializer.save()

            # Инвалидируем кеш списка ресурсов
            cache.delete('active_resources_list')

            # Возвращаем полные данные ресурса
            full_serializer = ResourceSerializer(resource, context={'request': request})
            return Response(full_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """
        PUT /resources/{id} - полное обновление ресурса
        """
        resource = get_object_or_404(Resource, pk=pk)
        serializer = ResourceUpdateSerializer(resource, data=request.data)

        if serializer.is_valid():
            updated_resource = serializer.save()

            # Инвалидируем кеши
            self._invalidate_resource_caches(resource.id)

            full_serializer = ResourceSerializer(updated_resource, context={'request': request})
            return Response(full_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        """
        PATCH /resources/{id} - частичное обновление ресурса
        """
        resource = get_object_or_404(Resource, pk=pk)
        serializer = ResourceUpdateSerializer(resource, data=request.data, partial=True)

        if serializer.is_valid():
            updated_resource = serializer.save()

            # Инвалидируем кеши
            self._invalidate_resource_caches(resource.id)

            full_serializer = ResourceSerializer(updated_resource, context={'request': request})
            return Response(full_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """
        DELETE /resources/{id} - деактивация ресурса
        """
        resource = get_object_or_404(Resource, pk=pk)

        # Деактивируем ресурс вместо полного удаления
        resource.is_active = False
        resource.save()

        # Инвалидируем кеши
        self._invalidate_resource_caches(resource.id)

        return Response(
            {'message': 'Ресурс успешно деактивирован'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='file')
    def upload_file(self, request, pk=None):
        """
        POST /resources/{id}/file - загрузка файла для ресурса
        """
        resource = get_object_or_404(Resource, pk=pk)

        if 'file' not in request.FILES:
            return Response(
                {'error': 'Файл не предоставлен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file = request.FILES['file']

        # Валидация файла
        validator = FileValidator()
        try:
            validator(uploaded_file)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Определяем MIME-тип по расширению
        mime_type = validator.get_mime_type(uploaded_file.name)

        # Создаем запись FileUpload
        file_upload = FileUpload.objects.create(
            owner_user=request.user,
            path=uploaded_file,
            size_bytes=uploaded_file.size,
            mime_type=mime_type,
            original_filename=uploaded_file.name
        )

        # Привязываем файл к ресурсу
        resource.file_path = file_upload.path
        resource.save()

        # Инвалидируем кеши ресурса
        self._invalidate_resource_caches(resource.id)

        file_serializer = FileUploadSerializer(file_upload, context={'request': request})

        return Response(file_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='file')
    def delete_file(self, request, pk=None):
        """
        DELETE /resources/{id}/file - удаление файла ресурса
        """
        resource = get_object_or_404(Resource, pk=pk)

        if not resource.file_path:
            return Response(
                {'error': 'Файл не прикреплен к ресурсу'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Находим связанный FileUpload объект
        file_upload = FileUpload.objects.filter(path=resource.file_path.name).first()

        # Удаляем файл из ресурса
        resource.file_path.delete(save=False)
        resource.file_path = None
        resource.save()

        # Удаляем запись FileUpload если существует
        if file_upload:
            file_upload.delete()

        # Инвалидируем кеши ресурса
        self._invalidate_resource_caches(resource.id)

        return Response(
            {'message': 'Файл успешно удален'},
            status=status.HTTP_200_OK
        )

    def _invalidate_resource_caches(self, resource_id):
        """
        Инвалидация кешей, связанных с ресурсом
        """
        cache_keys = [
            'active_resources_list',
            f'resource_detail_{resource_id}',
        ]

        # Инвалидируем кеш доступности для всех дат
        cache.delete_many([key for key in cache._cache.keys() if key.startswith('avail:')])

        for key in cache_keys:
            cache.delete(key)

        @action(detail=True, methods=['get'], url_path='availability')
        def availability(self, request, pk=None):
            """
            GET /resources/{id}/availability?date=YYYY-MM-DD
            Получение доступности ресурса на конкретную дату
            """
            resource = get_object_or_404(Resource, pk=pk)

            # Проверяем параметр date
            date_str = request.query_params.get('date')
            if not date_str:
                return Response(
                    {'error': 'Параметр date обязателен (формат: YYYY-MM-DD)'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Неверный формат даты. Используйте YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Проверяем, что дата не в прошлом
            if date < datetime.now().date():
                return Response(
                    {'error': 'Нельзя запросить доступность для прошедшей даты'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Получаем доступность через сервис (с кешированием)
            availability_data = AvailabilityService.get_resource_availability(resource.id, date)

            return Response(availability_data)

        @action(detail=False, methods=['get'], url_path='cache-stats')
        def cache_stats(self, request):
            """
            GET /resources/cache-stats
            Статистика кеша доступности (только для админов)
            """
            if not request.user.is_authenticated or request.user.role != 'admin':
                return Response(
                    {'error': 'Доступ запрещен'},
                    status=status.HTTP_403_FORBIDDEN
                )

            stats = AvailabilityCache.get_availability_stats()
            return Response(stats)