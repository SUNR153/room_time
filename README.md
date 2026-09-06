# RoomTime

REST API для аренды помещений/площадок с онлайн-оплатой: каталог ресурсов, бронирование по времени с защитой от двойного бронирования, оплата и уведомления.

## Возможности

- JWT-аутентификация (регистрация, логин, refresh, logout с блэклистингом токена)
- Каталог ресурсов (переговорки, залы и т.п.) с ценой за час и вложениями (фото/документы)
- Проверка доступности по дням с почасовыми слотами и кэшированием в Redis
- Бронирование по схеме **hold → confirm**: временное удержание слота на 10 минут, транзакционная защита от гонок при пересечении времени
- Автоматическое освобождение неподтверждённых holds по расписанию (Celery beat)
- Оплата подтверждённых бронирований (сумма считается по длительности × цена ресурса)
- Уведомления пользователю о ключевых событиях (оплата и т.д.)

## Стек

- **Backend:** Django, Django REST Framework, drf-spectacular (OpenAPI)
- **Auth:** JWT (djangorestframework-simplejwt) + блэклист токенов
- **DB:** PostgreSQL
- **Кэш / очереди:** Redis, Celery (+ Celery Beat для периодических задач)
- **Инфраструктура:** Docker / docker-compose

## Запуск через Docker

```bash
docker compose up --build
```

Поднимет Django, PostgreSQL и Redis согласно `.env` (см. `.env.example`).

## Запуск локально (без Docker)

```bash
python -m venv myvenv
myvenv\Scripts\activate       # Windows

pip install -r requirements.txt

cp .env.example .env
```

В `.env` укажи `POSTGRES_HOST=localhost` и `REDIS_HOST=localhost` (по умолчанию там имена Docker-сервисов `db`/`redis`) и подними Postgres + Redis локально.

```bash
python manage.py migrate
python manage.py runserver
```

Для фоновых задач (автоистечение holds) отдельно нужен воркер и планировщик:

```bash
celery -A roomtime worker --pool=solo -l info
celery -A roomtime beat -l info
```

## Тесты

```bash
python manage.py test
```

## Основные эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| POST | `/auth/register/` | Регистрация |
| POST | `/auth/login/` | Логин, выдаёт JWT access/refresh |
| POST | `/auth/refresh/` | Обновление access-токена |
| POST | `/auth/logout/` | Логаут (блэклист refresh-токена) |
| GET | `/auth/me/` | Текущий пользователь |
| GET | `/api/resources/` | Каталог ресурсов |
| GET | `/api/resources/<id>/availability/?date=YYYY-MM-DD` | Доступность по дням |
| POST | `/api/bookings/hold/` | Создать hold на слот |
| POST | `/api/bookings/confirm/` | Подтвердить hold |
| POST | `/api/bookings/<id>/cancel/` | Отменить бронирование |
| GET | `/api/bookings/mine/` | Мои бронирования |
| POST | `/api/payments/pay/` | Оплатить подтверждённое бронирование |
| GET | `/api/notifications/` | Мои уведомления |

Полная интерактивная документация (Swagger UI) — `/api/docs/`, OpenAPI-схема — `/api/schema/`.
