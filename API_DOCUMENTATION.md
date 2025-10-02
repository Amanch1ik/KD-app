# Karakol Delivery API Documentation

## Базовый URL
```
http://127.0.0.1:8000/api/
```

## Аутентификация
Для защищенных эндпоинтов используется JWT (SimpleJWT).

Получение токена:
```
POST /api/token/
{"username": "test", "password": "..."}
```

Обновление токена:
```
POST /api/token/refresh/
{"refresh": "..."}
```

Заголовок авторизации:
```
Authorization: Bearer <access_token>
```

## Эндпоинты

### 1. Категории (Categories)

#### Получить список всех категорий
```
GET /api/categories/
```

**Ответ:**
```json
[
    {
        "id": 1,
        "name": "Пицца",,
        "description": "Итальянская пицца"
    }
]
```

#### Создать новую категорию
```
POST /api/categories/
Content-Type: application/json

{
    "name": "Суши",
    "description": "Японская кухня"
}
```

#### Получить конкретную категорию
```
GET /api/categories/{id}/
```

#### Обновить категорию
```
PUT /api/categories/{id}/
PATCH /api/categories/{id}/
```

#### Удалить категорию
```
DELETE /api/categories/{id}/
```

### 2. Продукты (Products)

#### Получить список всех продуктов
```
GET /api/products/
GET /api/products/?restaurant={id}
```

**Ответ:**
```json
[
    {
        "id": 1,
        "name": "Маргарита",
        "description": "Классическая пицца с томатами и моцареллой",
        "price": "15.99",
        "category": 1,
        "category_name": "Пицца",
        "image": null,
        "available": true,
        "created_at": "2025-06-30T01:00:00Z"
    }
]
```

#### Получить продукты по категории
```
GET /api/products/by_category/?category_id=1
```

#### Создать новый продукт
```
POST /api/products/
Content-Type: application/json

{
    "name": "Пепперони",
    "description": "Пицца с пепперони",
    "price": "18.99",
    "category": 1,
    "available": true
}
```

#### Обновить продукт
```
PUT /api/products/{id}/
PATCH /api/products/{id}/
```

#### Удалить продукт
```
DELETE /api/products/{id}/
```

### 3. Заказы (Orders) - Требует аутентификации

#### Получить список заказов пользователя
```
GET /api/orders/
Authorization: Bearer your_token_here
```

**Ответ:**
```json
[
    {
        "id": 1,
        "customer": 1,
        "customer_username": "user123",
        "items": [
            {
                "id": 1,
                "product": 1,
                "product_name": "Маргарита",
                "quantity": 2,
                "price": "15.99"
            }
        ],
        "total_amount": "31.98",
        "status": "pending",
        "delivery_address": "ул. Ленина, 123",
        "phone_number": "+996555123456",
        "created_at": "2025-06-30T01:00:00Z",
        "updated_at": "2025-06-30T01:00:00Z"
    }
]
```

#### Создать новый заказ
```
POST /api/orders/
Authorization: Bearer your_token_here
Content-Type: application/json

{
    "total_amount": "31.98",
    "delivery_address": "ул. Ленина, 123",
    "phone_number": "+996555123456"
}
```

#### Обновить статус заказа
```
PATCH /api/orders/{id}/
Authorization: Bearer your_token_here

{
    "status": "confirmed"
}
```

## Статусы заказов
- `pending` - Ожидает подтверждения
- `confirmed` - Подтвержден
- `preparing` - Готовится
- `delivering` - Доставляется
- `delivered` - Доставлен
- `cancelled` - Отменен

## Коды ответов
- `200` - Успешно
- `201` - Создано
- `400` - Ошибка валидации
- `401` - Не авторизован
- `403` - Доступ запрещен
- `404` - Не найдено
- `500` - Ошибка сервера

## Примеры использования

### JavaScript (Fetch API)
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
        'Authorization': 'Bearer your_token_here'
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

### Python (requests)
```python
import requests

# Получить все категории
response = requests.get('http://127.0.0.1:8000/api/categories/')
categories = response.json()

# Создать продукт
data = {
    "name": "Пепперони",
    "description": "Пицца с пепперони",
    "price": "......",
    "category": 1,
    "available": True
}
response = requests.post('http://127.0.0.1:8000/api/products/', json=data)
```

## Для фронтенд-разработчиков

1. **Начните с получения списка категорий и продуктов**
2. **Для работы с заказами потребуется система аутентификации (JWT)**
3. **Все эндпоинты поддерживают CORS для фронтенд-приложений**
4. **Используйте фильтрацию по категориям/ресторану для каталога товаров**

## Тестирование API

Вы можете протестировать API через:
- Браузер (для GET запросов)
- Postman
- curl
- Django REST Framework Browsable API (встроенный интерфейс) 