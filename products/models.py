from ckeditor.fields import RichTextField
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field
from imagekit.models.fields import ImageSpecField
from pilkit.processors import ResizeToFill
import bleach

from django_countries.fields import CountryField

ALLOWED_ATTRIBUTES = bleach.sanitizer.ALLOWED_ATTRIBUTES
ALLOWED_STYLES = ['color', 'font-weight', 'text-decoration', 'background-color', 'font-size']


class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название категории")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="URL")
    icon = models.CharField(max_length=50, verbose_name="Иконка", help_text="CSS-класс иконки Font Awesome")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            original_slug = slugify(self.name)
            queryset = Product.objects.filter(slug__iexact=original_slug).exclude(id=self.id)
            count = queryset.count()
            slug = original_slug
            while queryset.exists():
                count += 1
                slug = f"{original_slug}-{count}"
                queryset = Product.objects.filter(slug__iexact=slug).exclude(id=self.id)
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products:category_detail', args=[self.slug])

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

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            original_slug = slugify(self.name)
            queryset = Product.objects.filter(slug__iexact=original_slug).exclude(id=self.id)
            count = queryset.count()
            slug = original_slug
            while queryset.exists():
                count += 1
                slug = f"{original_slug}-{count}"
                queryset = Product.objects.filter(slug__iexact=slug).exclude(id=self.id)
            self.slug = slug
        super().save(*args, **kwargs)

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
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name='Способ оплаты')
    notes = models.TextField(verbose_name='Примечания к заказу', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    paid = models.BooleanField(default=False, verbose_name='Оплачен')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Общая сумма')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing', verbose_name='Статус')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f'Заказ {self.id} от {self.user.username}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_absolute_url(self):
        return reverse('orders:order_detail', args=[str(self.id)])

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def get_cost(self):
        return self.price * self.quantity

    def __str__(self):
        return f'{self.quantity} x {self.product.name}'

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='Товар')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    rating = models.PositiveIntegerField(default=5, verbose_name='Рейтинг')
    comment = models.TextField(verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return f'Отзыв от {self.user.username} на {self.product.name}'

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist', verbose_name='Пользователь')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='in_wishlists', verbose_name='Товар')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    def __str__(self):
        return f'{self.user.username} - {self.product.name}'

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']




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



class StaticPage(models.Model):
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL')
    content = CKEditor5Field('Содержимое', config_name='default')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Статическая страница'
        verbose_name_plural = 'Статические страницы'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('static_page', kwargs={'slug': self.slug})




