from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import Resource, FileUpload


class ResourceSerializer(serializers.ModelSerializer):
    """Сериализатор для ресурса"""
    has_file = serializers.BooleanField(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = [
            'id', 'name', 'location', 'capacity',
            'file_path', 'file_url', 'has_file',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_file_url(self, obj):
        """Возвращает URL файла если он существует"""
        if obj.file_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_path.url)
        return None


class ResourceCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания ресурса"""

    class Meta:
        model = Resource
        fields = ['name', 'location', 'capacity', 'is_active']

    def validate_capacity(self, value):
        """Валидация вместимости"""
        if value < 1:
            raise ValidationError('Вместимость должна быть не менее 1')
        return value


class ResourceUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления ресурса"""

    class Meta:
        model = Resource
        fields = ['name', 'location', 'capacity', 'is_active']

    def validate_capacity(self, value):
        """Валидация вместимости"""
        if value < 1:
            raise ValidationError('Вместимость должна быть не менее 1')
        return value


class FileUploadSerializer(serializers.ModelSerializer):
    """Сериализатор для загрузки файлов"""
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.FloatField(read_only=True)

    class Meta:
        model = FileUpload
        fields = [
            'id', 'original_filename', 'mime_type',
            'file_size_mb', 'file_url', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_file_url(self, obj):
        """Возвращает URL файла"""
        if obj.path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.path.url)
        return None