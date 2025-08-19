# Руководство по интеграции фронтенда с бэкендом

## 🔧 Необходимые исправления в фронтенде

### 1. **Регистрация пользователей**
```javascript
// Добавить функцию регистрации
const registerUser = async (userData) => {
    const response = await fetch(`${appState.apiBaseUrl}register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: userData.username,
            password: userData.password,
            phone_number: userData.phone_number
        })
    });
    
    if (response.ok) {
        const data = await response.json();
        appState.token = data.access;
        localStorage.setItem('authToken', data.access);
        return true;
    }
    return false;
};
```

### 2. **Создание заказов через API**
```javascript
// Заменить alert на реальный API запрос
const createOrder = async (orderData) => {
    const response = await fetch(`${appState.apiBaseUrl}orders/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${appState.token}`
        },
        body: JSON.stringify({
            restaurant: orderData.restaurant_id,
            items: orderData.items.map(item => ({
                product: item.id,
                quantity: item.quantity
            })),
            delivery_address: orderData.address,
            payment_method: orderData.payment_method
        })
    });
    
    if (response.ok) {
        const order = await response.json();
        return order;
    }
    throw new Error('Failed to create order');
};
```

### 3. **Отслеживание заказов**
```javascript
// Добавить реальное отслеживание
const trackOrder = async (orderId) => {
    const response = await fetch(`${appState.apiBaseUrl}orders/${orderId}/`, {
        headers: { 'Authorization': `Bearer ${appState.token}` }
    });
    
    if (response.ok) {
        const order = await response.json();
        return order;
    }
    throw new Error('Failed to fetch order');
};
```

### 4. **История заказов**
```javascript
// Получение истории заказов пользователя
const getOrderHistory = async () => {
    const response = await fetch(`${appState.apiBaseUrl}orders/`, {
        headers: { 'Authorization': `Bearer ${appState.token}` }
    });
    
    if (response.ok) {
        const orders = await response.json();
        return orders;
    }
    throw new Error('Failed to fetch order history');
};
```

## 🚀 Дополнительные функции для реализации

### 1. **Поиск и фильтрация**
```javascript
// Поиск ресторанов
const searchRestaurants = async (query) => {
    const response = await fetch(`${appState.apiBaseUrl}restaurants/?search=${query}`, {
        headers: { 'Authorization': `Bearer ${appState.token}` }
    });
    return response.json();
};
```

### 2. **Промокоды**
```javascript
// Применение промокода
const applyPromoCode = async (code) => {
    const response = await fetch(`${appState.apiBaseUrl}promo-codes/apply/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${appState.token}`
        },
        body: JSON.stringify({ code })
    });
    return response.json();
};
```

### 3. **Уведомления**
```javascript
// Регистрация устройства для push-уведомлений
const registerDevice = async (token) => {
    const response = await fetch(`${appState.apiBaseUrl}device-tokens/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${appState.token}`
        },
        body: JSON.stringify({
            registration_id: token,
            device_type: 'web'
        })
    });
    return response.json();
};
```

## 📱 Рекомендации по улучшению

### 1. **Обработка ошибок**
```javascript
// Добавить глобальную обработку ошибок
const handleApiError = (error) => {
    if (error.status === 401) {
        // Токен истек, перенаправить на логин
        localStorage.removeItem('authToken');
        navigateTo('login');
    } else if (error.status === 400) {
        // Показать ошибку валидации
        showError(error.message);
    }
};
```

### 2. **Кэширование данных**
```javascript
// Улучшить кэширование
const cacheData = (key, data, ttl = 300000) => {
    const cacheItem = {
        data,
        timestamp: Date.now(),
        ttl
    };
    localStorage.setItem(`cache_${key}`, JSON.stringify(cacheItem));
};

const getCachedData = (key) => {
    const cached = localStorage.getItem(`cache_${key}`);
    if (cached) {
        const item = JSON.parse(cached);
        if (Date.now() - item.timestamp < item.ttl) {
            return item.data;
        }
    }
    return null;
};
```

### 3. **Загрузка и состояния**
```javascript
// Добавить индикаторы загрузки
const showLoading = () => {
    getElement('main-content').innerHTML = `
        <div class="flex items-center justify-center h-64">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
    `;
};
```

## 🔗 Полная интеграция

Фронтенд готов к интеграции! Основные моменты:

1. **API эндпоинты совпадают** ✅
2. **JWT авторизация настроена** ✅
3. **Структура данных совместима** ✅
4. **UI/UX современный и удобный** ✅

Нужно только заменить mock-данные на реальные API вызовы в указанных местах.
