from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.safestring import mark_safe
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST
from django_filters.views import FilterView

from accounts.models import UserActivity
from .cart import Cart
from .filters import ProductFilter
from .forms import OrderCreateForm, ReviewForm
from .models import Product, Category, OrderItem, Review, Wishlist, Order, StaticPage, SubCategory
from .utils import fuzzy_search_suggestions


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
        return redirect('products:product_detail', product_id=product.id)

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
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    paginator = Paginator(wishlist_items, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'wishlist.html', {'page_obj': page_obj})

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

def highlight(text, query):
    """Подсвечивает найденный текст с помощью тега <mark>."""
    if not query:
        return text
    # Для упрощения выделяем все вхождения query (регистр зависит от используемых методов)
    return mark_safe(text.replace(query, f'<mark>{query}</mark>'))
def product_search(request):
    query = request.GET.get('q', '').strip()
    sort_option = request.GET.get('sort', 'name')  # параметр сортировки из GET
    category_filter = request.GET.get('category', '')  # фильтр по категории
    price_min = request.GET.get('price_min', '')
    price_max = request.GET.get('price_max', '')

    # Ключ для кэша (включим в него все параметры, чтобы кэшировать конкретные результаты)
    cache_key = f"search_{query}_{sort_option}_{category_filter}_{price_min}_{price_max}"
    results = cache.get(cache_key)

    if results is None:
        # Если запрос пустой - показываем все товары.
        products = Product.objects.all()

        # Фильтруем по запросу (по названию, описанию, категории)
        if query:
            products = products.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            ).distinct()

        # Фильтрация по категории, бренду и цене
        if category_filter:
            products = products.filter(category__slug=category_filter)

        if price_min.isdigit():
            products = products.filter(price__gte=float(price_min))
        if price_max.isdigit():
            products = products.filter(price__lte=float(price_max))

        # Сортировка (по цене, по дате добавления, по популярности)
        # Предположим: name (по имени), price (по цене), -price (по убыванию цены),
        # created_at (по дате), -created_at (по убыванию даты)
        # popularity не указана в модели, но предположим что сортируем по количеству просмотров или по created_at
        valid_sorts = ['name', 'price', '-price', 'created_at', '-created_at']
        if sort_option not in valid_sorts:
            sort_option = 'name'
        products = products.order_by(sort_option)

        # Если ничего не найдено, попробуем предложить "Did you mean?" (fuzzy search)
        did_you_mean = []
        if query and not products.exists():
            # Используем вашу логику или внешнюю утилиту для fuzzy search
            did_you_mean = fuzzy_search_suggestions(query)  # например, ['product1', 'product2']

        results = {
            'products': products,
            'did_you_mean': did_you_mean,
            'query': query,
        }

        # Кэшируем результаты на 5 минут
        cache.set(cache_key, results, 300)
    else:
        products = results['products']
        did_you_mean = results['did_you_mean']
        query = results['query']

    # Пагинация
    paginator = Paginator(products, 12)  # 12 товаров на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Подсветим запрос в названиях и описаниях
    # В шаблоне вместо product.name и product.description используем product.highlighted_name и product.highlighted_description
    highlighted_products = []
    for p in page_obj:
        p.highlighted_name = highlight(p.name, query)
        p.highlighted_description = highlight(p.description, query)
        highlighted_products.append(p)

    return render(request, 'product_search.html', {
        'query': query,
        'page_obj': page_obj,
        'did_you_mean': did_you_mean,
        'selected_sort': sort_option,
        'selected_category': category_filter,
        'price_min': price_min,
        'price_max': price_max,
        'highlighted_products': highlighted_products,
    })

def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    products = []
    categories = []
    if query:
        products = list(Product.objects.filter(name__icontains=query).values('id', 'name'))
        categories = list(Category.objects.filter(name__icontains=query).values('slug', 'name'))
    return JsonResponse({
        'products': products,
        'categories': categories
    })

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


def subcategory_detail(request, category_slug, subcategory_slug):
    category = get_object_or_404(Category, slug=category_slug)
    subcategory = get_object_or_404(SubCategory, category=category, slug=subcategory_slug)
    products = Product.objects.filter(category=category)  # Если у вас есть связь товара с подкатегорией, отфильтруйте и по ней
    return render(request, 'subcategory_detail.html', {
        'category': category,
        'subcategory': subcategory,
        'products': products
    })