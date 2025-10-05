document.addEventListener('DOMContentLoaded', () => {
    // Простая корзина и загрузка продуктов из API
    const apiBase = '/api/endpoints/';
    const cart = JSON.parse(localStorage.getItem('cart_v1') || '[]');

    function saveCart() {
        localStorage.setItem('cart_v1', JSON.stringify(cart));
    }

    function renderCartSummary() {
        const summary = document.getElementById('cart-summary');
        if (!summary) return;
        const total = cart.reduce((s, i) => s + Number(i.price) * Number(i.quantity), 0);
        const qty = cart.reduce((s, i) => s + Number(i.quantity), 0);
        summary.innerHTML = `
            <div class="cart-summary-inner">
                <div class="cart-summary-left">
                    <div class="cart-total-label">Итого:</div>
                    <div class="cart-total-value">${total.toLocaleString('ru-RU')} so'm</div>
                </div>
                <button id="checkout-btn" class="checkout-button" ${qty === 0 ? 'disabled' : ''}>Оформить</button>
            </div>
        `;
        const checkoutBtn = document.getElementById('checkout-btn');
        if (checkoutBtn) {
            checkoutBtn.addEventListener('click', async () => {
                try {
                    // Send minimal data; server will read existing cart or create order
                    const res = await fetch('/api/endpoints/cart/checkout/', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')||''}`, 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    });
                    if (!res.ok) throw new Error('Checkout failed');
                    const data = await res.json();
                    showToast('Заказ оформлен');
                    // Clear local cart; rely on server order
                    cart.length = 0; saveCart(); renderCartSummary();
                    window.location.href = '/';
                } catch (e) {
                    showToast('Ошибка оформления заказа');
                }
            });
        }
    }

    function showToast(message) {
        let toast = document.getElementById('toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'toast';
            toast.style.position = 'fixed';
            toast.style.bottom = '20px';
            toast.style.left = '50%';
            toast.style.transform = 'translateX(-50%)';
            toast.style.background = 'rgba(0,0,0,0.8)';
            toast.style.color = '#fff';
            toast.style.padding = '8px 12px';
            toast.style.borderRadius = '6px';
            toast.style.zIndex = '9999';
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.style.opacity = '1';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => { toast.style.opacity = '0'; }, 1500);
    }

    function renderProducts(products) {
        const grid = document.querySelector('.products-grid');
        if (!grid) return;
        grid.innerHTML = '';
        const list = Array.isArray(products) ? products : (products?.results || []);
        window.loadedProducts = list;
        list.forEach(p => {
            const card = document.createElement('div');
            card.className = `product-card`;
            card.innerHTML = `
                <div class="product-card-header">
                    <div class="product-card-title">${p.translations?.ru?.name || p.translations?.en?.name || 'Product'}</div>
                </div>
                <div class="product-card-content">
                    <div class="product-card-subtitle">${p.translations?.ru?.description || ''}</div>
                    <div class="product-card-footer">
                        <div class="product-card-price">${Number(p.price).toLocaleString('ru-RU')} so'm</div>
                        <div class="cart-qty" data-id="${p.id}">
                            <button class="qty-btn" data-action="dec" data-id="${p.id}">−</button>
                            <span class="qty-val">${(JSON.parse(localStorage.getItem('cart_v1')||'[]').find(i=>i.id===p.id)?.quantity)||0}</span>
                            <button class="qty-btn" data-action="inc" data-id="${p.id}">+</button>
                        </div>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
        // (removed) global delegated handler will be added below
    }

    async function loadProducts() {
        const endpointsToTry = [apiBase + 'products/'];
        const altBase = '/endpoints/';
        endpointsToTry.push(altBase + 'products/');
        endpointsToTry.push('/api/endpoints/products/');
        for (const endpoint of endpointsToTry) {
            try {
                const res = await fetch(endpoint);
                if (!res.ok) { console.debug('Endpoint failed', endpoint, 'status', res.status); continue; }
                const data = await res.json();
                renderProducts(data);
                return;
            } catch (err) {
                // try next
            }
        }
        console.error('Products load error: all endpoints failed');
        showToast('Не удалось загрузить данные о продуктах. Проверьте подключение к API.');
    }

    function updateQtyBadge(id) {
        const el = document.querySelector(`.cart-qty[data-id="${id}"] .qty-val`);
        if (!el) return;
        const it = cart.find(x => String(x.id) === String(id));
        el.textContent = it ? it.quantity : 0;
    }

    // Initialize delegated click handler for cart +/- and add
    if (!window.__cartClickListenerAdded) {
        document.addEventListener('click', function(ev) {
            const qtyBtn = ev.target.closest('.qty-btn');
            if (!qtyBtn) return;
            const id = qtyBtn.getAttribute('data-id');
            const action = qtyBtn.getAttribute('data-action');
            const prod = (window.loadedProducts || []).find(x => String(x.id) === String(id));
            if (!prod) return;
            let item = cart.find(i => i.id === prod.id);
            if (action === 'inc') {
                if (item) item.quantity++;
                else item = cart[cart.push({ id: prod.id, title: prod.translations?.ru?.name || prod.translations?.en?.name || prod.id, price: Number(prod.price), quantity: 1 }) - 1];
            } else if (action === 'dec') {
                if (item) {
                    item.quantity--;
                    if (item.quantity <= 0) {
                        const idx = cart.findIndex(i => i.id === prod.id);
                        if (idx !== -1) cart.splice(idx, 1);
                    }
                }
            }
            saveCart();
            updateQtyBadge(prod.id);
            renderCartSummary();
        });
        window.__cartClickListenerAdded = true;
    }

    loadProducts();
    renderCartSummary();

    // Modal logic
    const productModal = document.getElementById('product-detail-modal');
    if (productModal) {
        productModal.querySelectorAll('.close-button').forEach(b => b.addEventListener('click', () => productModal.style.display = 'none'));
    }
});
