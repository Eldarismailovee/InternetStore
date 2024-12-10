from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from django_filters.views import FilterView

from accounts.models import UserActivity
from .cart import Cart
from .filters import ProductFilter
from .forms import OrderCreateForm, ReviewForm
from .models import Product, Category, OrderItem, Review, Wishlist, Order, StaticPage


def home(request):
    featured_products = Product.objects.filter(is_featured=True)
    categories = Category.objects.all()
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'current_year': datetime.now().year,
    }
    return render(request, 'home.html', context)
@require_POST
def add_to_cart(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    if quantity > product.stock:
        messages.error(request, f"Извините, доступно только {product.stock} единиц товара.")
    else:
        cart.add(product=product, quantity=quantity)
        messages.success(request, "Товар добавлен в корзину.")
    return redirect('products:cart_detail')


def get_currency_symbol(currency_code):
    symbols = {
        'MDL': 'L',
        'USD': '$',
        'EUR': '€',
    }
    return symbols.get(currency_code, '')


@login_required
def cart_detail(request):
    cart = Cart(request)

    # Handle currency selection
    if request.method == 'POST' and 'currency' in request.POST:
        currency = request.POST.get('currency', 'MDL')
        request.session['currency'] = currency
    else:
        currency = request.session.get('currency', 'MDL')

    currency_symbol = get_currency_symbol(currency)

    context = {
        'cart': cart,
        'currency': currency,
        'currency_symbol': currency_symbol,
        'current_year': datetime.now().year,
    }
    return render(request, 'cart_detail.html', context)
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('products:cart_detail')
@login_required
def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.error(request, 'Ваша корзина пуста.')
        return redirect('home')
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()
            # Добавляем товары в заказ
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )
            # Очищаем корзину
            cart.clear()
            messages.success(request, 'Заказ успешно оформлен!')
            return redirect('home')
    else:
        form = OrderCreateForm()
    return render(request, 'order_create.html', {'cart': cart, 'form': form})
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.all()  # Используя related_name='products'
    context = {
        'category': category,
        'products': products,
        'current_year': datetime.now().year,
    }
    return render(request, 'category_detail.html', context)
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # Логика отображения продукта
    if request.user.is_authenticated:
        UserActivity.objects.create(
            user=request.user,
            activity_type='Просмотр товара',
            description=f'Просмотрел товар: {product.name}'
        )
    return render(request, 'product_detail.html', {'product': product})


@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    existing_review = Review.objects.filter(product=product, user=request.user).first()
    if existing_review:
        messages.error(request, 'Вы уже оставили отзыв на этот товар.')
        return redirect('product_detail', product_id=product.id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Ваш отзыв успешно добавлен!")
            return redirect('products:product_detail', id=product.id)  # Используйте 'id' вместо 'product_id'
    else:
        form = ReviewForm()
    return render(request, 'add_review.html', {'form': form, 'product': product})

@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, 'Товар добавлен в список желаний.')
    else:
        messages.info(request, 'Товар уже в вашем списке желаний.')
    return redirect('products:product_detail', product_id=product.id)

@login_required
def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.success(request, 'Товар удалён из списка желаний.')
    return redirect('wishlist')

@login_required
def view_wishlist(request):
    # Получаем все элементы Wishlist для текущего пользователя
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    context = {
        'wishlist_items': wishlist_items
    }
    return render(request, 'wishlist.html', context)

@login_required
@cache_page(60 * 15)
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'accounts/order_history.html', {'orders': orders})

class ProductListView(FilterView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    filterset_class = ProductFilter
    paginate_by = 12  # Количество товаров на странице

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            # Получаем список ID продуктов, находящихся в списке желаний пользователя
            wishlist_product_ids = Wishlist.objects.filter(user=user).values_list('product_id', flat=True)
            context['wishlist_product_ids'] = set(wishlist_product_ids)
        else:
            context['wishlist_product_ids'] = set()
        return context


def product_search(request):
    return None


@require_POST
def update_quantity(request):
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity'))
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.update(product=product, quantity=quantity)
    item_total_price = cart.get_item_total_price(product)
    cart_total_price = cart.get_total_price()
    return JsonResponse({
        'item_total_price': float(item_total_price),
        'cart_total_price': float(cart_total_price),
    })


@require_POST
def remove_item(request):
    product_id = request.POST.get('product_id')
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    cart_total_price = cart.get_total_price()
    cart_empty = len(cart) == 0
    return JsonResponse({
        'cart_total_price': cart_total_price,
        'cart_empty': cart_empty,
    })

def static_page(request, slug):
    page = get_object_or_404(StaticPage, slug=slug)
    return render(request, 'static_page.html', {'page': page})


def static_page_preview(request, pk):
    """
    Представление для предпросмотра статической страницы.
    """
    static_page = get_object_or_404(StaticPage, pk=pk)
    return render(request, 'products/staticpage_preview.html', {'static_page': static_page})

