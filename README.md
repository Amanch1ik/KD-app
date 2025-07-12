# Karakol Delivery - Backend API

## Описание проекта
Backend API для системы доставки еды в Караколе. Проект построен на Django REST Framework.

## Технологии
- **Django 5.2.3** - основной фреймворк
- **Django REST Framework 3.16.0** - API
- **SQLite** - база данных
- **Django CORS Headers** - поддержка CORS для фронтенда

## Установка и запуск

### 1. Клонирование и настройка
```bash
git clone <repository-url>
cd KarakolDelivery
```

### 2. Активация виртуального окружения
```bash
# Windows
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Миграции базы данных
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Создание суперпользователя (если нужно)
```bash
python manage.py createsuperuser
```

### 6. Добавление тестовых данных
```bash
python test_data.py
```

### 7. Запуск сервера
```bash
python manage.py runserver
```

## Доступные URL

- **Главная страница**: http://127.0.0.1:8000/
- **API Root**: http://127.0.0.1:8000/api/
- **Админка**: http://127.0.0.1:8000/admin/

## API Endpoints

### Категории
- `GET /api/categories/` - список всех категорий
- `POST /api/categories/` - создать категорию
- `GET /api/categories/{id}/` - получить категорию
- `PUT /api/categories/{id}/` - обновить категорию
- `DELETE /api/categories/{id}/` - удалить категорию

### Продукты
- `GET /api/products/` - список всех продуктов
- `POST /api/products/` - создать продукт
- `GET /api/products/{id}/` - получить продукт
- `PUT /api/products/{id}/` - обновить продукт
- `DELETE /api/products/{id}/` - удалить продукт
- `GET /api/products/by_category/?category_id=1` - продукты по категории

### Заказы (требует аутентификации)
- `GET /api/orders/` - список заказов пользователя
- `POST /api/orders/` - создать заказ
- `GET /api/orders/{id}/` - получить заказ
- `PATCH /api/orders/{id}/` - обновить статус заказа

## Модели данных

### Category (Категория)
- `name` - название категории
- `description` - описание категории

### Product (Продукт)
- `name` - название продукта
- `description` - описание продукта
- `price` - цена
- `category` - связь с категорией
- `image` - изображение продукта
- `available` - доступность
- `created_at` - дата создания

### Order (Заказ)
- `customer` - клиент (связь с User)
- `products` - продукты (через OrderItem)
- `total_amount` - общая сумма
- `status` - статус заказа
- `delivery_address` - адрес доставки
- `phone_number` - номер телефона
- `created_at` - дата создания
- `updated_at` - дата обновления

### OrderItem (Элемент заказа)
- `order` - связь с заказом
- `product` - связь с продуктом
- `quantity` - количество
- `price` - цена за единицу

## Статусы заказов
- `pending` - Ожидает подтверждения
- `confirmed` - Подтвержден
- `preparing` - Готовится
- `delivering` - Доставляется
- `delivered` - Доставлен
- `cancelled` - Отменен

## Для фронтенд-разработчиков

### Аутентификация
Для работы с заказами требуется аутентификация. Используйте:
- Session Authentication (для браузерных приложений)
- Token Authentication (для мобильных приложений)

### CORS
API настроен для работы с фронтенд-приложениями на:
- http://localhost:3000 (React/Vue dev server)
- http://127.0.0.1:3000
- http://localhost:8080 (Vue dev server)
- http://127.0.0.1:8080

### Примеры запросов

#### JavaScript (Fetch API)
```javascript
// Получить все продукты
fetch('http://127.0.0.1:8000/api/products/')
    .then(response => response.json())
    .then(data => console.log(data));

// Создать заказ
fetch('http://127.0.0.1:8000/api/orders/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token your_token_here'
    },
    body: JSON.stringify({
        total_amount: "31.98",
        delivery_address: "ул. Ленина, 123",
        phone_number: "+996555123456"
    })
})
.then(response => response.json())
.then(data => console.log(data));
```

#### Python (requests)
```python
import requests

# Получить все категории
response = requests.get('http://127.0.0.1:8000/api/categories/')
categories = response.json()

# Создать продукт
data = {
    "name": "Пепперони",
    "description": "Пицца с пепперони",
    "price": "18.99",
    "category": 1,
    "available": True
}
response = requests.post('http://127.0.0.1:8000/api/products/', json=data)
```

## Пагинация
API поддерживает пагинацию. По умолчанию 20 элементов на страницу.
```
GET /api/products/?page=2
```

## Фильтрация
- По категории: `/api/products/by_category/?category_id=1`
- По доступности: `/api/products/?available=true`

## Разработка

### Добавление новых моделей
1. Создайте модель в `delivery/models.py`
2. Создайте сериализатор в `delivery/serializers.py`
3. Создайте ViewSet в `delivery/views.py`
4. Добавьте URL в `delivery/urls.py`
5. Зарегистрируйте в админке `delivery/admin.py`
6. Создайте и примените миграции

### Тестирование
```bash
python manage.py test
```

## Деплой
Для продакшена:
1. Измените `DEBUG = False` в settings.py
2. Настройте `ALLOWED_HOSTS`
3. Используйте PostgreSQL вместо SQLite
4. Настройте статические файлы
5. Используйте WSGI сервер (Gunicorn)

## Контакты
Для вопросов по API обращайтесь к backend-разработчик(+996551697296/whatsapp,telegram)
9
---

**Версия**: 1.0.0  
**Дата**: Июнь 2025  
**Автор**: Айтбеков Аманбол 

INSTALLED_APPS += ['corsheaders']
MIDDLEWARE.insert(0, 'corsheaders.middleware.CorsMiddleware')
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',  # фронт
]

### TEST 123