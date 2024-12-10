# accounts/models.py
import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from django.utils import timezone
import pytz

from products.models import Category

TIME_ZONE_CHOICES = tuple(zip(pytz.all_timezones, pytz.all_timezones))

def user_directory_path(instance, filename):

    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'

    return f'user_{instance.user.id}/{filename}'

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(
        upload_to=user_directory_path,
        default='default_avatar.jpg',
        blank=True
    )
    bio = models.TextField(max_length=500, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, db_index=True)
    address = models.CharField(max_length=255, blank=True)
    twitter = models.URLField(max_length=200, blank=True, verbose_name='Twitter')
    facebook = models.URLField(max_length=200, blank=True, verbose_name='Facebook')
    instagram = models.URLField(max_length=200, blank=True, verbose_name='Instagram')
    linkedin = models.URLField(max_length=200, blank=True, verbose_name='LinkedIn')
    receive_newsletters = models.BooleanField(default=True, verbose_name='Получать новости и акции')
    receive_notifications = models.BooleanField(default=True, verbose_name='Получать уведомления о заказах')
    last_activity = models.DateTimeField(default=timezone.now, verbose_name='Последняя активность')
    ONLINE_THRESHOLD = timedelta(minutes=1)
    time_zone = models.CharField(
        max_length=32,
        choices=TIME_ZONE_CHOICES,
        default='UTC',
        verbose_name='Часовой пояс'
    )

    def is_online(self):
        return timezone.now() - self.last_activity <= self.ONLINE_THRESHOLD

    class Meta:
        ordering = ['user__username']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['birth_date']),
        ]

    def __str__(self):
        return f'Профиль пользователя {self.user.username}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.avatar and os.path.isfile(self.avatar.path):
            try:
                img = Image.open(self.avatar.path)

                # Конвертируем изображение в RGB, если это необходимо
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Изменяем размер изображения
                output_size = (300, 300)
                img.thumbnail(output_size)

                # Определяем формат изображения
                img_format = img.format if img.format else 'JPEG'

                # Сохраняем изображение с указанным форматом
                img.save(self.avatar.path, format=img_format)

            except Exception as e:
                # Логирование ошибки или другие действия
                print(f'Ошибка при сохранении изображения: {e}')

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.address_line1}, {self.city}, {self.country}"

class PaymentMethod(models.Model):
    PAYMENT_TYPES = [
        ('credit_card', 'Кредитная карта'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Банковский перевод'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    type = models.CharField(max_length=20, choices=PAYMENT_TYPES, verbose_name='Тип оплаты')
    details = models.CharField(max_length=255, verbose_name='Детали оплаты')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    card_number = models.CharField(max_length=16)
    card_holder = models.CharField(max_length=100)
    expiry_date = models.DateField()
    cvv = models.CharField(max_length=4)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"**** **** **** {self.card_number[-4:]}"

class NotificationSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=False)

    def __str__(self):
        return f"Настройки уведомлений для {self.user.username}"

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} at {self.timestamp}"

class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} подписан на {self.category.name}"

class UserLoginHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    session_key = models.CharField(max_length=128, blank=True)
    login_datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-login_datetime',)

    def __str__(self):
        return f"{self.user} logged in at {self.login_datetime} from {self.ip_address}"

class AdminSettings(models.Model):
    """
    Модель для хранения настроек административной панели.
    """
    site_logo = models.ImageField(upload_to='admin_logo/', blank=True, null=True, verbose_name='Логотип сайта')
    contact_email = models.EmailField(default='noreply@example.com', verbose_name='Контактный Email')
    site_timezone = models.CharField(
        max_length=32,
        choices=TIME_ZONE_CHOICES,
        default='UTC',
        verbose_name='Часовой пояс сайта'
    )
    welcome_message = models.TextField(default='Добро пожаловать в административную панель!', verbose_name='Приветственное сообщение')

    def __str__(self):
        return "Настройки Административной Панели"

    class Meta:
        verbose_name = "Настройки Административной Панели"
