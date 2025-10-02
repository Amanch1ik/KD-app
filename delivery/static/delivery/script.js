document.addEventListener('DOMContentLoaded', () => {
    // Простая корзина и загрузка продуктов из API
    const apiBase = '/api/endpoints/';
    const cart = JSON.parse(localStorage.getItem('cart_v1') || '[]');

    function saveCart() {
        localStorage.setItem('cart_v1', JSON.stringify(cart));
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
                        <button class="add-to-cart-button" data-id="${p.id}">+</button>
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

    // Initialize delegated click handler for adding to cart (once)
    if (!window.__cartClickListenerAdded) {
        document.addEventListener('click', function(ev) {
            const btn = ev.target.closest('.add-to-cart-button');
            if (!btn) return;
            const id = btn.getAttribute('data-id');
            const prod = (window.loadedProducts || []).find(x => String(x.id) === String(id));
            if (!prod) return;
            const existing = cart.find(i => i.id === prod.id);
            if (existing) existing.quantity++;
            else cart.push({ id: prod.id, title: prod.translations?.ru?.name || prod.translations?.en?.name || prod.id, price: Number(prod.price), quantity: 1 });
            saveCart();
            showToast('Добавлено в корзину');
        });
        window.__cartClickListenerAdded = true;
    }

    loadProducts();

    // Modal logic
    const productModal = document.getElementById('product-detail-modal');
    if (productModal) {
        productModal.querySelectorAll('.close-button').forEach(b => b.addEventListener('click', () => productModal.style.display = 'none'));
    }
});
