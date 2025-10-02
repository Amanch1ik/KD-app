document.addEventListener('DOMContentLoaded', () => {
    // Корзина
    const cartItems = [];
    const cartItemsList = document.querySelector('.cart-items-list');
    const totalAmountElement = document.querySelector('.total-amount span:last-child');
    const addToCartButtons = document.querySelectorAll('.add-to-cart-button');

    addToCartButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            const productCard = e.target.closest('.product-card');
            const title = productCard.querySelector('.product-card-title').textContent;
            const price = parseFloat(productCard.querySelector('.product-card-price').textContent.replace(' so\'m', ''));

            // Добавление товара в корзину
            const existingItem = cartItems.find(item => item.title === title);
            if (existingItem) {
                existingItem.quantity++;
            } else {
                cartItems.push({ title, price, quantity: 1 });
            }

            updateCart();
        });
    });

    function updateCart() {
        // Очистка текущих элементов корзины
        cartItemsList.innerHTML = '';

        // Обновление элементов корзины
        let totalAmount = 0;
        cartItems.forEach(item => {
            const cartItemElement = document.createElement('div');
            cartItemElement.classList.add('cart-item');
            cartItemElement.innerHTML = `
                <div class="cart-item-details">
                    <span class="cart-item-title">${item.title} x ${item.quantity}</span>
                    <span class="cart-item-price">${item.price * item.quantity} so'm</span>
                </div>
                <div class="quantity-control">
                    <button class="quantity-button minus">-</button>
                    <span class="quantity">${item.quantity}</span>
                    <button class="quantity-button plus">+</button>
                </div>
            `;
            cartItemsList.appendChild(cartItemElement);
            totalAmount += item.price * item.quantity;
        });

        // Обновление общей суммы
        totalAmountElement.textContent = `${totalAmount} so'm`;
    }

    // Модальное окно для деталей продукта
    const productCards = document.querySelectorAll('.product-card');
    const productModal = document.getElementById('product-detail-modal');
    const closeModalButton = productModal.querySelector('.close-button');

    productCards.forEach(card => {
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.add-to-cart-button')) {
                const title = card.querySelector('.product-card-title').textContent;
                const description = card.querySelector('.product-card-description').textContent;
                const price = card.querySelector('.product-card-price').textContent;
                const image = card.querySelector('.product-card-image').src;

                productModal.querySelector('.modal-product-title').textContent = title;
                productModal.querySelector('.modal-product-description').textContent = description;
                productModal.querySelector('.modal-product-price').textContent = price;
                productModal.querySelector('.modal-product-image').src = image;

                productModal.style.display = 'block';
            }
        });
    });

    closeModalButton.addEventListener('click', () => {
        productModal.style.display = 'none';
    });
});
