from autoslug import AutoSlugField
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field
from imagekit.models.fields import ImageSpecField
from pilkit.processors import ResizeToFill
from django_countries.fields import CountryField

import bleach

# Ваши константы bleach
ALLOWED_ATTRIBUTES = bleach.sanitizer.ALLOWED_ATTRIBUTES
ALLOWED_STYLES = ['color', 'font-weight', 'text-decoration', 'background-color', 'font-size']

# ----------------------------------------------------------------------
# Category
# ----------------------------------------------------------------------

class CategoryQuerySet(models.QuerySet):
    def with_products_count(self):
        """
        Аннотирует количество товаров (Product) в каждой категории.
        """
        return self.annotate(products_count=models.Count('products'))


class CategoryManager(models.Manager):
    def get_queryset(self):
        # Можно сразу подгружать что-то, но здесь пример без select_related
        return CategoryQuerySet(self.model, using=self._db)

    def with_products_count(self):
        return self.get_queryset().with_products_count()


class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название категории")
    slug = AutoSlugField(populate_from='name', unique=True)
    icon = models.CharField(max_length=50, verbose_name="Иконка",
                            help_text="CSS-класс иконки Font Awesome")

    # Подключаем менеджер
    objects = CategoryManager()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        ВНИМАНИЕ: вы используете Product.objects.filter(slug__iexact=...).
        Скорее всего вы хотели бы проверять slug в модели Category, а не Product.
        Если это ошибка — замените Product.objects на Category.objects.
        """
        if not self.slug:
            original_slug = slugify(self.name)
            queryset = Category.objects.filter(slug__iexact=original_slug).exclude(id=self.id)
            count = queryset.count()
            new_slug = original_slug
            while queryset.exists():
                count += 1
                new_slug = f"{original_slug}-{count}"
                queryset = Category.objects.filter(slug__iexact=new_slug).exclude(id=self.id)
            self.slug = new_slug

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:category_detail', args=[self.slug])


# ----------------------------------------------------------------------
# SubCategory
# ----------------------------------------------------------------------

class SubCategoryQuerySet(models.QuerySet):
    def with_parent_category(self):
        """
        Пример: select_related('category') для более эффективной выборки,
        когда нужно часто обращаться к subcategory.category.
        """
        return self.select_related('category')


class SubCategoryManager(models.Manager):
    def get_queryset(self):
        return SubCategoryQuerySet(self.model, using=self._db)

    def with_parent_category(self):
        return self.get_queryset().with_parent_category()


class SubCategory(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name="Родительская категория"
    )
    name = models.CharField(max_length=255, verbose_name="Название подкатегории")
    slug = AutoSlugField(populate_from='name', unique=True)
    icon = models.CharField(
        max_length=50,
        verbose_name="Иконка",
        help_text="CSS-класс иконки Font Awesome",
        blank=True,
        null=True
    )

    objects = SubCategoryManager()

    class Meta:
        verbose_name = "Подкатегория"
        verbose_name_plural = "Подкатегории"

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def save(self, *args, **kwargs):
        """
        Аналогичное замечание о Product.objects — вероятно,
        вы хотели бы проверять Slug в SubCategory.objects.
        """
        if not self.slug:
            original_slug = slugify(self.name)
            queryset = SubCategory.objects.filter(slug__iexact=original_slug).exclude(id=self.id)
            count = queryset.count()
            new_slug = original_slug
            while queryset.exists():
                count += 1
                new_slug = f"{original_slug}-{count}"
                queryset = SubCategory.objects.filter(slug__iexact=new_slug).exclude(id=self.id)
            self.slug = new_slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:subcategory_detail', args=[self.category.slug, self.slug])


# ----------------------------------------------------------------------
# Product
# ----------------------------------------------------------------------

class ProductQuerySet(models.QuerySet):
    def featured(self):
        return self.filter(is_featured=True)

    def in_stock(self):
        return self.filter(stock__gt=0)

    def with_category(self):
        return self.select_related('category')


class ProductManager(models.Manager):
    def get_queryset(self):
        # Пример: сразу добавляем select_related('category') во все запросы
        return ProductQuerySet(self.model, using=self._db).select_related('category')

    def featured(self):
        return self.get_queryset().featured()

    def in_stock(self):
        return self.get_queryset().in_stock()

    def with_category(self):
        return self.get_queryset().with_category()


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="URL")
    related_products = models.ManyToManyField('self', blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Категория"
    )
    description = CKEditor5Field(verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена", db_index=True)
    image = models.ImageField(upload_to='products/', verbose_name="Изображение")
    is_featured = models.BooleanField(default=False, verbose_name="На главной")
    stock = models.PositiveIntegerField(default=0, verbose_name="Количество на складе")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    image_thumbnail = ImageSpecField(
        source='image',
        processors=[ResizeToFill(50, 50)],
        format='JPEG',
        options={'quality': 60}
    )

    class Meta:
        indexes = [
            models.Index(fields=['price']),
            models.Index(fields=['created_at']),
        ]

    objects = ProductManager()

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            original_slug = slugify(self.name)
            queryset = Product.objects.filter(slug__iexact=original_slug).exclude(id=self.id)
            count = queryset.count()
            new_slug = original_slug
            while queryset.exists():
                count += 1
                new_slug = f"{original_slug}-{count}"
                queryset = Product.objects.filter(slug__iexact=new_slug).exclude(id=self.id)
            self.slug = new_slug
        super().save(*args, **kwargs)


# ----------------------------------------------------------------------
# Order
# ----------------------------------------------------------------------

class OrderQuerySet(models.QuerySet):
    def paid(self):
        return self.filter(paid=True)

    def unpaid(self):
        return self.filter(paid=False)

    def by_user(self, user):
        return self.filter(user=user)

    def with_items(self):
        # prefetch_related -> items + подгрузка product
        return self.prefetch_related('items__product').select_related('user')


class OrderManager(models.Manager):
    def get_queryset(self):
        # Можно добавить select_related('user') по умолчанию
        return OrderQuerySet(self.model, using=self._db).select_related('user')

    def paid(self):
        return self.get_queryset().paid()

    def unpaid(self):
        return self.get_queryset().unpaid()

    def by_user(self, user):
        return self.get_queryset().by_user(user)

    def with_items(self):
        return self.get_queryset().with_items()


class Order(models.Model):
    STATUS_CHOICES = [
        ('processing', 'В обработке'),
        ('shipped', 'Отправлено'),
        ('delivered', 'Доставлено'),
        ('cancelled', 'Отменено'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Кредитная карта'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Банковский перевод'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    first_name = models.CharField(max_length=50, verbose_name='Имя')
    last_name = models.CharField(max_length=50, verbose_name='Фамилия')
    email = models.EmailField(verbose_name='Email')
    address = models.CharField(max_length=250, verbose_name='Адрес')
    postal_code = models.CharField(max_length=20, verbose_name='Почтовый индекс')
    city = models.CharField(max_length=100, verbose_name='Город')
    country = CountryField(verbose_name='Страна')
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name='Способ оплаты'
    )
    notes = models.TextField(verbose_name='Примечания к заказу', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    paid = models.BooleanField(default=False, verbose_name='Оплачен')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Общая сумма')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='processing',
        verbose_name='Статус'
    )

    objects = OrderManager()

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f'Заказ {self.id} от {self.user.username}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_absolute_url(self):
        return reverse('orders:order_detail', args=[str(self.id)])


# ----------------------------------------------------------------------
# OrderItem
# ----------------------------------------------------------------------

class OrderItemQuerySet(models.QuerySet):
    def with_product(self):
        return self.select_related('product')

    def with_order_and_product(self):
        return self.select_related('order', 'product')


class OrderItemManager(models.Manager):
    def get_queryset(self):
        return OrderItemQuerySet(self.model, using=self._db)

    def with_product(self):
        return self.get_queryset().with_product()

    def with_order_and_product(self):
        return self.get_queryset().with_order_and_product()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    objects = OrderItemManager()

    def get_cost(self):
        return self.price * self.quantity

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'


# ----------------------------------------------------------------------
# Review
# ----------------------------------------------------------------------

class ReviewQuerySet(models.QuerySet):
    def by_user(self, user):
        return self.filter(user=user)

    def by_product(self, product):
        return self.filter(product=product)

    def with_user(self):
        return self.select_related('user')

    def with_product(self):
        return self.select_related('product')


class ReviewManager(models.Manager):
    def get_queryset(self):
        # По умолчанию добавим select_related('product', 'user')
        return ReviewQuerySet(self.model, using=self._db).select_related('product', 'user')

    def by_user(self, user):
        return self.get_queryset().by_user(user)

    def by_product(self, product):
        return self.get_queryset().by_product(product)

    def with_user(self):
        return self.get_queryset().with_user()

    def with_product(self):
        return self.get_queryset().with_product()


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='reviews', verbose_name='Товар')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    rating = models.PositiveIntegerField(default=5, verbose_name='Рейтинг')
    comment = models.TextField(verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    objects = ReviewManager()

    def __str__(self):
        return f'Отзыв от {self.user.username} на {self.product.name}'

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')


# ----------------------------------------------------------------------
# Wishlist
# ----------------------------------------------------------------------

class WishlistQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user)

    def with_product(self):
        return self.select_related('product')

    def with_user(self):
        return self.select_related('user')


class WishlistManager(models.Manager):
    def get_queryset(self):
        # Часто нужно подгружать product и user (зависит от логики)
        return WishlistQuerySet(self.model, using=self._db).select_related('product', 'user')

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def with_product(self):
        return self.get_queryset().with_product()

    def with_user(self):
        return self.get_queryset().with_user()


class Wishlist(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlist',
        verbose_name='Пользователь'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='in_wishlists',
        verbose_name='Товар'
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    objects = WishlistManager()

    def __str__(self):
        return f'{self.user.username} - {self.product.name}'

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']


# ----------------------------------------------------------------------
# CartItem (не модель, менеджер не требуется)
# ----------------------------------------------------------------------
class CartItem:
    def __init__(self, product, quantity):
        self.product = product
        self.quantity = quantity

    def price_converted(self, currency):
        exchange_rates = {
            'MDL': 1,
            'USD': 0.056,
            'EUR': 0.048,
        }
        rate = exchange_rates.get(currency, 1)
        return self.product.price * rate

    def total_price_converted(self, currency):
        return self.price_converted(currency) * self.quantity


# ----------------------------------------------------------------------
# StaticPage
# ----------------------------------------------------------------------

class StaticPageQuerySet(models.QuerySet):
    def by_slug(self, slug_value):
        return self.filter(slug=slug_value)


class StaticPageManager(models.Manager):
    def get_queryset(self):
        return StaticPageQuerySet(self.model, using=self._db)

    def by_slug(self, slug_value):
        return self.get_queryset().by_slug(slug_value)


class StaticPage(models.Model):
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL')
    content = CKEditor5Field('Содержимое', config_name='default')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    objects = StaticPageManager()

    class Meta:
        verbose_name = 'Статическая страница'
        verbose_name_plural = 'Статические страницы'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('static_page', kwargs={'slug': self.slug})
