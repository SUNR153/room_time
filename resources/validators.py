from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import os


class FileSizeValidator:
    """
    Валидатор для проверки размера файла
    """

    def __init__(self, max_size_mb=10):
        """
        :param max_size_mb: максимальный размер файла в МБ
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def __call__(self, value):
        """
        Проверяет размер файла
        """
        if value.size > self.max_size_bytes:
            raise ValidationError(
                _('Размер файла не должен превышать %(max_size)s МБ. '
                  'Ваш файл: %(actual_size)s МБ.'),
                code='file_too_large',
                params={
                    'max_size': self.max_size_bytes / (1024 * 1024),
                    'actual_size': round(value.size / (1024 * 1024), 2)
                }
            )


class MimeTypeValidator:
    """
    Валидатор для проверки MIME-типов файлов
    """

    # Разрешенные MIME-типы
    ALLOWED_MIME_TYPES = {
        # Изображения
        'image/jpeg': ['jpg', 'jpeg'],
        'image/png': ['png'],
        'image/gif': ['gif'],
        'image/webp': ['webp'],
        'image/svg+xml': ['svg'],

        # Документы
        'application/pdf': ['pdf'],

        # Текстовые документы
        'application/msword': ['doc'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['docx'],
        'application/vnd.ms-excel': ['xls'],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['xlsx'],
        'application/vnd.ms-powerpoint': ['ppt'],
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['pptx'],

        # Текстовые файлы
        'text/plain': ['txt'],
        'text/csv': ['csv'],
    }

    # Альтернативные MIME-типы (для совместимости)
    ALTERNATIVE_MIME_TYPES = {
        'image/pjpeg': 'image/jpeg',
        'image/x-png': 'image/png',
    }

    def __init__(self, allowed_mimes=None):
        """
        :param allowed_mimes: список разрешенных MIME-типов
        """
        if allowed_mimes is None:
            self.allowed_mimes = list(self.ALLOWED_MIME_TYPES.keys())
        else:
            self.allowed_mimes = allowed_mimes

    def __call__(self, value):
        """
        Проверяет MIME-тип файла
        """
        mime_type = self._get_mime_type(value)

        # Проверяем основной и альтернативные MIME-типы
        if (mime_type not in self.allowed_mimes and
                mime_type not in self.ALTERNATIVE_MIME_TYPES):
            raise ValidationError(
                _('Недопустимый тип файла: %(mime_type)s. '
                  'Разрешены: %(allowed_types)s'),
                code='invalid_mime_type',
                params={
                    'mime_type': mime_type,
                    'allowed_types': ', '.join(sorted(self.allowed_mimes))
                }
            )

        # Дополнительная проверка по расширению файла
        self._validate_extension(value.name, mime_type)

    def _get_mime_type(self, file):
        """
        Определяет MIME-тип файла на основе его содержимого и имени
        """
        # Сначала проверяем content_type из запроса
        if hasattr(file, 'content_type') and file.content_type:
            mime_type = file.content_type

            # Нормализуем MIME-тип
            if mime_type in self.ALTERNATIVE_MIME_TYPES:
                mime_type = self.ALTERNATIVE_MIME_TYPES[mime_type]

            return mime_type

        # Если content_type недоступен, определяем по расширению
        return self._get_mime_type_by_extension(file.name)

    def _get_mime_type_by_extension(self, filename):
        """
        Определяет MIME-тип по расширению файла
        """
        ext = self._get_file_extension(filename).lower()

        for mime_type, extensions in self.ALLOWED_MIME_TYPES.items():
            if ext in extensions:
                return mime_type

        return 'application/octet-stream'

    def _get_file_extension(self, filename):
        """
        Извлекает расширение файла
        """
        return os.path.splitext(filename)[1][1:]  # Убираем точку

    def _validate_extension(self, filename, mime_type):
        """
        Дополнительная проверка соответствия расширения и MIME-типа
        """
        ext = self._get_file_extension(filename).lower()
        expected_extensions = self.ALLOWED_MIME_TYPES.get(mime_type, [])

        if expected_extensions and ext not in expected_extensions:
            raise ValidationError(
                _('Расширение файла .%(extension)s не соответствует '
                  'заявленному MIME-типу %(mime_type)s. '
                  'Ожидаемые расширения: %(expected_extensions)s'),
                code='extension_mismatch',
                params={
                    'extension': ext,
                    'mime_type': mime_type,
                    'expected_extensions': ', '.join(expected_extensions)
                }
            )


class FileExtensionValidator:
    """
    Валидатор для проверки расширений файлов (дополнительная защита)
    """

    ALLOWED_EXTENSIONS = {
        'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',  # Изображения
        'pdf',  # PDF
        'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',  # Office документы
        'txt', 'csv',  # Текстовые файлы
    }

    def __init__(self, allowed_extensions=None):
        """
        :param allowed_extensions: множество разрешенных расширений
        """
        if allowed_extensions is None:
            self.allowed_extensions = self.ALLOWED_EXTENSIONS
        else:
            self.allowed_extensions = allowed_extensions

    def __call__(self, value):
        """
        Проверяет расширение файла
        """
        ext = self._get_file_extension(value.name).lower()

        if ext not in self.allowed_extensions:
            raise ValidationError(
                _('Расширение .%(extension)s не разрешено. '
                  'Разрешены: %(allowed_extensions)s'),
                code='invalid_extension',
                params={
                    'extension': ext,
                    'allowed_extensions': ', '.join(sorted(self.allowed_extensions))
                }
            )

    def _get_file_extension(self, filename):
        """
        Извлекает расширение файла
        """
        return os.path.splitext(filename)[1][1:]  # Убираем точку


class ImageDimensionsValidator:
    """
    Валидатор для проверки размеров изображений (опционально)
    """

    def __init__(self, max_width=None, max_height=None, min_width=None, min_height=None):
        """
        :param max_width: максимальная ширина
        :param max_height: максимальная высота
        :param min_width: минимальная ширина
        :param min_height: минимальная высота
        """
        self.max_width = max_width
        self.max_height = max_height
        self.min_width = min_width
        self.min_height = min_height

    def __call__(self, value):
        """
        Проверяет размеры изображения
        """
        # Проверяем, является ли файл изображением
        if not value.content_type.startswith('image/'):
            return  # Не изображение, пропускаем проверку

        try:
            from PIL import Image
            import io

            # Читаем изображение
            image = Image.open(io.BytesIO(value.read()))
            value.seek(0)  # Возвращаем указатель

            width, height = image.size

            # Проверяем ограничения
            if self.max_width and width > self.max_width:
                raise ValidationError(
                    _('Ширина изображения (%(width)spx) превышает максимальную '
                      'допустимую (%(max_width)spx)'),
                    code='image_too_wide',
                    params={'width': width, 'max_width': self.max_width}
                )

            if self.max_height and height > self.max_height:
                raise ValidationError(
                    _('Высота изображения (%(height)spx) превышает максимальную '
                      'допустимую (%(max_height)spx)'),
                    code='image_too_tall',
                    params={'height': height, 'max_height': self.max_height}
                )

            if self.min_width and width < self.min_width:
                raise ValidationError(
                    _('Ширина изображения (%(width)spx) меньше минимальной '
                      'допустимой (%(min_width)spx)'),
                    code='image_too_narrow',
                    params={'width': width, 'min_width': self.min_width}
                )

            if self.min_height and height < self.min_height:
                raise ValidationError(
                    _('Высота изображения (%(height)spx) меньше минимальной '
                      'допустимой (%(min_height)spx)'),
                    code='image_too_short',
                    params={'height': height, 'min_height': self.min_height}
                )

        except ImportError:
            # PIL не установлен, пропускаем проверку размеров
            pass
        except Exception as e:
            raise ValidationError(
                _('Не удалось проверить размеры изображения: %(error)s'),
                code='image_validation_error',
                params={'error': str(e)}
            )


# Готовые валидаторы для удобства использования
default_file_validators = [
    FileSizeValidator(max_size_mb=10),
    MimeTypeValidator(),
    FileExtensionValidator(),
]

image_validators = [
    FileSizeValidator(max_size_mb=5),
    MimeTypeValidator(allowed_mimes=[
        'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'
    ]),
    FileExtensionValidator(allowed_extensions={'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'}),
]

document_validators = [
    FileSizeValidator(max_size_mb=10),
    MimeTypeValidator(allowed_mimes=[
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ]),
    FileExtensionValidator(allowed_extensions={'pdf', 'doc', 'docx'}),
]