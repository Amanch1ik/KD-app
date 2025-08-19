# Karakol Delivery Backend API

Полнофункциональный бэкенд для приложения доставки еды в Караколе.

## 🚀 Быстрый старт

### Установка и запуск

```bash
# Клонирование репозитория
git clone https://github.com/Amanch1ik/Karakol-delivery-backend.git
cd Karakol-delivery-backend

# Создание виртуального окружения
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt

# Миграции базы данных
python manage.py migrate

# Создание суперпользователя
python manage.py createsuperuser

# Запуск сервера
python manage.py runserver
```

Сервер будет доступен по адресу: `http://127.0.0.1:8000/`

## 📚 API Документация

### Базовый URL
```
http://127.0.0.1:8000/api/
```

### Аутентификация

API использует JWT токены для аутентификации.

#### Регистрация пользователя
```http
POST /api/register/
Content-Type: application/json

{
    "username": "testuser",
    "email": "test@example.com",
    "password": "your_password",
    "password2": "your_password",
    "phone_number": "+996777123456"
}
```

#### Получение токена (логин)
```http
POST /api/token/
Content-Type: application/json

{
    "username": "testuser",
    "password": "your_password"
}
```

#### Обновление токена
```http
POST /api/token/refresh/
Content-Type: application/json

{
    "refresh": "your_refresh_token"
}
```

### Использование токена
Добавьте заголовок к запросам:
```
Authorization: Bearer your_access_token
```

## 🏪 Основные API эндпоинты

### Категории товаров
```http
GET /api/categories/          # Список всех категорий
GET /api/categories/{id}/     # Детали категории
```

### Товары
```http
GET /api/products/                    # Список всех товаров
GET /api/products/{id}/              # Детали товара
GET /api/products/by_category/?category_id=1  # Товары по категории
```

### Рестораны
```http
GET /api/restaurants/        # Список активных ресторанов
GET /api/restaurants/{id}/   # Детали ресторана
```

### Корзина и заказы

#### Добавление товара в корзину
```http
POST /api/order-items/
Authorization: Bearer your_token
Content-Type: application/json

{
    "product": 1,
    "quantity": 2
}
```

#### Просмотр корзины
```http
GET /api/order-items/
Authorization: Bearer your_token
```

#### Создание заказа
```http
POST /api/orders/
Authorization: Bearer your_token
Content-Type: application/json

{
    "delivery_address": "ул. Ленина, 10, кв. 5",
    "phone_number": "+996555987654",
    "customer_name": "Иван Иванов",
    "restaurant": 1,
    "payment_method": "cash"
}
```

#### Просмотр заказов
```http
GET /api/orders/             # Мои заказы (клиент) или все (админ)
GET /api/orders/{id}/        # Детали заказа
```

### Курьеры

#### Доступные курьеры
```http
GET /api/delivery-persons/available/
Authorization: Bearer your_token
```

#### Обновление местоположения курьера
```http
POST /api/delivery-persons/{id}/update_location/
Authorization: Bearer your_token
Content-Type: application/json

{
    "latitude": 42.4907,
    "longitude": 78.3936,
    "status": "available"
}
```

### Отслеживание заказов
```http
GET /api/orders/{id}/tracking/
Authorization: Bearer your_token
```

### Рейтинги
```http
POST /api/orders/{id}/rate/
Authorization: Bearer your_token
Content-Type: application/json

{
    "score": 5,
    "comment": "Отличная доставка!"
}
```

### Платежи
```http
GET /api/payments/                    # Мои платежи
POST /api/payments/{id}/initiate/     # Инициация платежа
POST /api/payments/{id}/callback/     # Обработка платежа
```

### Карта
```http
GET /api/map/data/                    # Все данные для карты
GET /api/map/delivery_persons/        # Только курьеры
GET /api/map/active_orders/           # Только активные заказы
```

## 👥 Роли пользователей

### Клиент
- Просмотр товаров и ресторанов
- Управление корзиной
- Создание и отслеживание заказов
- Оценка доставки

### Курьер
- Просмотр назначенных заказов
- Обновление местоположения
- Принятие/отмена заказов
- Просмотр статистики и баланса

### Администратор
- Полный доступ ко всем данным
- Управление пользователями
- Назначение курьеров
- Просмотр статистики

### Партнер-ресторан
- Управление товарами ресторана
- Просмотр заказов ресторана

## 🔧 Настройки для фронтенда

### CORS
CORS настроен для разработки:
```python
CORS_ALLOW_ALL_ORIGINS = True
```

### Пагинация
По умолчанию: 20 элементов на страницу
```http
GET /api/products/?page=1
```

### Поиск
```http
GET /api/products/?search=пицца
GET /api/restaurants/?search=ресторан
```

### Сортировка
```http
GET /api/products/?ordering=price
GET /api/products/?ordering=-price
```

## 📱 Push-уведомления

Система уведомлений настроена для:
- Новых заказов для курьеров
- Обновления статуса заказа для клиентов
- Назначения курьера

### Регистрация токена устройства
```http
POST /api/device-tokens/
Authorization: Bearer your_token
Content-Type: application/json

{
    "registration_id": "device_token_here",
    "device_type": "android"
}
```

## 🗺️ Интеграция с картами

### 2GIS API
Настроена интеграция с 2GIS для:
- Расчет маршрутов
- Определение расстояний
- Геокодирование адресов

### Получение маршрута
```http
GET /api/orders/{id}/get_route/
Authorization: Bearer your_token
```

## 💳 Платежные системы

Подготовлена интеграция с:
- PayBox
- MBANK
- Элькарт
- Visa/MasterCard

## 🔐 Безопасность

- JWT токены с коротким временем жизни
- Автоматическое обновление токенов
- Ролевая система доступа
- Валидация данных на всех уровнях

## 📊 Мониторинг

- Логирование всех операций
- Отслеживание производительности
- Мониторинг ошибок

## 🚀 Развертывание

### Продакшн настройки
1. Измените `DEBUG = False` в settings.py
2. Настройте `ALLOWED_HOSTS`
3. Используйте PostgreSQL вместо SQLite
4. Настройте статические файлы
5. Добавьте SSL сертификат

### Docker (опционально)
```bash
docker build -t karakol-delivery .
docker run -p 8000:8000 karakol-delivery
```

## 📞 Поддержка

Для вопросов и поддержки:
- Создайте Issue в GitHub
- Обратитесь к документации API
- Проверьте логи сервера

## 📄 Лицензия

MIT License