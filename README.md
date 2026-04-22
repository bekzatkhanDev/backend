# Backend API - Руководство по запуску

Django REST API с PostgreSQL/PostGIS для такси-приложения.

## Требования

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)

## Быстрый старт с Docker

### 1. Настройка переменных окружения

Скопируйте файл примера и настройте его:

```bash
cp .env.example .env
```

Отредактируйте файл `.env`:

```env
SECRET_KEY=ваш-секретный-ключ
DEBUG=True
POSTGRES_DB=taxservice
POSTGRES_USER=ваше-имя-пользователя
POSTGRES_PASSWORD=ваш-пароль
GOOGLE_API_KEY=ваш-google-api-ключ
CORS_ALLOW_ALL_ORIGINS=True
HOST_IP=localhost
```

### 2. Запуск контейнеров

```bash
docker-compose up -d
```

Это запустит:
- PostgreSQL с PostGIS (база данных) - порт 5432
- PGAdmin (управление БД) - порт 8080
- Django backend API - порт 8000

### 3. Выполнение миграций

```bash
docker exec tax_service-backend-1 python manage.py migrate
```

### 4. Заполнение тестовыми данными (опционально)

```bash
docker exec tax_service-backend-1 python manage.py seed_data
```

Создается:
- **1 администратор**: +77000000000 (пароль: admin1234)
- **10 клиентов**: +77010000001 - +77010000010 (пароль: test1234)
- **30 водителей**: +77020000001 - +77020000030 (пароль: test1234)

## Локальная разработка (без Docker)

### 1. Создайте виртуальное окружение

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 2. Установите зависимости

```bash
pip install -r requirements.txt
```

### 3. Настройте базу данных

Убедитесь, что PostgreSQL с PostGIS установлен и запущен. Создайте базу данных:

```sql
CREATE DATABASE taxservice;
```

### 4. Настройте переменные окружения

```bash
cp .env.example .env
# Отредактируйте .env файл
```

### 5. Выполните миграции

```bash
python manage.py migrate
```

### 6. Запустите сервер

```bash
python manage.py runserver
```

API будет доступно по адресу: http://localhost:8000

## API Эндпоинты

- `/api/auth/` - Аутентификация
- `/api/tariffs/` - Тарифы
- `/api/estimates/` - Расчет стоимости
- `/api/nearby-drivers/` - Ближайшие водители
- `/api/trips/` - Поездки
- `/api/place-search/` - Поиск мест (Google Places)

## Получение Google API Key

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект
3. Включите следующие API:
   - Maps SDK for Android
   - Maps SDK for iOS
   - Directions API
   - Places API
4. Создайте API ключ и добавьте его в `.env`

## Тестирование

### Django Unit Tests

Запуск всех тестов:

```bash
# С Docker
docker exec tax_service-backend-1 python manage.py test taxi.tests

# Локально
python manage.py test taxi.tests
```

Запуск с подробным выводом:

```bash
docker exec tax_service-backend-1 python manage.py test taxi.tests -v 2
```

Запуск конкретного тестового класса:

```bash
docker exec tax_service-backend-1 python manage.py test taxi.tests.AuthTests
docker exec tax_service-backend-1 python manage.py test taxi.tests.TripTests
docker exec tax_service-backend-1 python manage.py test taxi.tests.PaymentTests
```

### Тестовые аккаунты

### Вход как администратор
Телефон: `+77000000000`
Пароль: `admin1234`

> Администратор также имеет доступ к Django Admin (`/admin/`) как суперпользователь.

### Вход как клиент
Телефон: `+77010000001`
Пароль: `test1234`

### Вход как водитель
Телефон: `+77020000001`
Пароль: `test1234`

---

## AQA Тестирование (Security Analysis)

### Bandit - Статический анализ безопасности

Bandit - это инструмент для поиска распространённых проблем безопасности в Python-коде.

#### Установка

```bash
pip install bandit
```

#### Запуск

```bash
# Сканирование всей папки taxi (исключая миграции и тесты)
bandit -r taxi/ -x taxi/migrations,taxi/tests.py

# Сканирование конкретных файлов
bandit taxi/views.py taxi/models.py taxi/serializers.py

# С подробным выводом
bandit -r taxi/ -v
```

#### Результаты

- **High/Medium**: Требуют немедленного исправления
- **Low**: Рекомендации по улучшению

#### Пример конфигурации (.bandit)

Создайте файл `backend/.bandit`:

```yaml
[bandit]
exclude = 
    migrations
    tests
    venv
    */migrations/*
    */tests/*

skips = B105,B106
```

#### Запуск с конфигом

```bash
bandit -c .bandit taxi/
```

## Структура проекта

```
backend/
├── config/          # Настройки Django
├── taxi/            # Основное приложение
│   ├── models.py    # Модели БД
│   ├── views.py     # API представления
│   ├── serializers.py # DRF сериализаторы
│   ├── urls.py      # Маршруты
│   └── services/    # Бизнес-логика
├── manage.py        # Django management
├── requirements.txt # Зависимости
└── Dockerfile       # Docker образ
```

## Команды Docker

```bash
# Просмотр логов
docker-compose logs -f backend

# Перезапуск
docker-compose restart backend

# Остановка
docker-compose down
```
