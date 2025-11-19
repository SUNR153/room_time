from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
import os
import uuid
from .validators import default_file_validators, image_validators, document_validators

User = get_user_model()


def resource_file_upload_path(instance, filename):
    """Генерирует путь для загрузки файлов ресурсов"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('resources', filename)


class Resource(models.Model):
    """Модель ресурса для бронирования"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        verbose_name='Название ресурса'
    )
    location = models.CharField(
        max_length=500,
        verbose_name='Местоположение'
    )
    capacity = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Вместимость',
        help_text='Максимальное количество человек'
    )
    file_path = models.FileField(
        upload_to=resource_file_upload_path,
        null=True,
        blank=True,
        verbose_name='Прикрепленный файл',
        help_text='Изображение или документ с правилами'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        help_text='Неактивные ресурсы скрыты из поиска'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )



    class Meta:
        db_table = 'resources'
        verbose_name = 'Ресурс'
        verbose_name_plural = 'Ресурсы'
        indexes = [
            models.Index(fields=['is_active', 'created_at']),
            models.Index(fields=['location']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.location})"


class FileUpload(models.Model):
    """Модель для отслеживания загруженных файлов"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_files',
        verbose_name='Владелец файла'
    )
    path = models.FileField(
        upload_to='uploads/%Y/%m/%d/',
        verbose_name='Путь к файлу'
    )
    size_bytes = models.BigIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Размер файла (байты)'
    )
    mime_type = models.CharField(
        max_length=100,
        verbose_name='MIME-тип файла'
    )
    original_filename = models.CharField(
        max_length=255,
        verbose_name='Оригинальное имя файла'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата загрузки'
    )

    class Meta:
        db_table = 'file_uploads'
        verbose_name = 'Загруженный файл'
        verbose_name_plural = 'Загруженные файлы'
        indexes = [
            models.Index(fields=['owner_user', 'created_at']),
            models.Index(fields=['mime_type']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_filename} ({self.owner_user.email})"

    def delete(self, *args, **kwargs):
        """Удаляет физический файл при удалении записи"""
        if self.path:
            if os.path.isfile(self.path.path):
                os.remove(self.path.path)
        super().delete(*args, **kwargs)