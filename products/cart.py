from decimal import Decimal

from .models import Product


class Cart:
    def __init__(self, request):
        """
        Инициализируем корзину
        """
        self.session = request.session
        self.user = request.user if request.user.is_authenticated else None
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, product, quantity=1, update_quantity=False):
        product_id = str(product.id)
        quantity = int(quantity)
        if quantity > product.stock:
            quantity = product.stock  # Ограничиваем количество доступным на складе
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(product.price)}
        if update_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
            # Дополнительная проверка после добавления
            if self.cart[product_id]['quantity'] > product.stock:
                self.cart[product_id]['quantity'] = product.stock
        self.save()

    def save(self):
        # Обновление сессии cart
        self.session['cart'] = self.cart
        # Отметить сессию как "измененную", чтобы убедиться, что она сохранится
        self.session.modified = True

    def remove(self, product):
        """
        Удаление товара из корзины
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        currency = self.session.get('currency', 'MDL')
        exchange_rates = {
            'MDL': 1,
            'USD': 0.056,
            'EUR': 0.048,
        }
        rate = exchange_rates.get(currency, 1)
        for product in products:
            cart_item = self.cart[str(product.id)]
            cart_item['product'] = product
            cart_item['price'] = Decimal(cart_item['price']) * rate
            cart_item['total_price'] = cart_item['price'] * cart_item['quantity']
            yield cart_item

    def __len__(self):
        """
        Подсчет всех товаров в корзине
        """
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """
        Подсчет общей стоимости товаров в корзине
        """
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        # Очистка корзины
        self.session['cart'] = {}
        self.session.modified = True

    def update(self, product, quantity):
        """
        Update quantity of a product in the cart
        """
        product_id = str(product.id)
        if product_id in self.cart:
            self.cart[product_id]['quantity'] = quantity
            self.save()

    def get_item_total_price(self, product):
        """
        Get total price for a single item in the cart
        """
        product_id = str(product.id)
        if product_id in self.cart:
            return Decimal(self.cart[product_id]['price']) * self.cart[product_id]['quantity']
        return Decimal(0)


