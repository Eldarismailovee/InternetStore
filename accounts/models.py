import uuid
from datetime import timedelta
from zoneinfo import available_timezones

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
from PIL import Image
from solo.models import SingletonModel
import logging

logger = logging.getLogger(__name__)


# Валидатор для номера телефона
phone_validator = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Номер должен быть в формате: '+999999999' (до 15 цифр)"
)

# Выбор часовых поясов
TIME_ZONE_CHOICES = tuple(zip(available_timezones(), available_timezones()))

# Путь для загрузки аватаров
def user_directory_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"  # Уникальное имя файла
    return f"users/{instance.user.id}/avatars/{filename}"


# -----------------------------------------------------------------------
# Пример кастомного QuerySet и Manager для Profile
# -----------------------------------------------------------------------
class ProfileQuerySet(models.QuerySet):
    def online(self):
        """
        Возвращает queryset с профилями, которые считаются "онлайн".
        """
        now = timezone.now()
        return self.filter(last_activity__gte=now - Profile.ONLINE_THRESHOLD)

    def offline(self):
        """
        Возвращает queryset с профилями, которые считаются "оффлайн".
        """
        now = timezone.now()
        return self.filter(last_activity__lt=now - Profile.ONLINE_THRESHOLD)


class ProfileManager(models.Manager):
    def get_queryset(self):
        """
        Переопределяем get_queryset, чтобы сразу делать select_related('user')
        и работать с нашим кастомным QuerySet (ProfileQuerySet).
        """
        return (
            ProfileQuerySet(self.model, using=self._db)
            .select_related('user')
        )

    def online(self):
        return self.get_queryset().online()

    def offline(self):
        return self.get_queryset().offline()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(
        upload_to=user_directory_path,
        default='default_avatar.jpg',
        blank=True
    )
    bio = models.TextField(max_length=500, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        validators=[phone_validator]
    )
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

    # Подключаем наш кастомный менеджер
    objects = ProfileManager()

    class Meta:
        ordering = ['user__username']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['birth_date']),
        ]

    def __str__(self):
        return f'Профиль пользователя {self.user.username}'

    def save(self, *args, **kwargs):
        """
        Переопределяем сохранение, чтобы обработать аватар при его изменении.
        """
        if self.pk:
            old = Profile.objects.filter(pk=self.pk).first()
            if old and old.avatar != self.avatar:
                self.process_avatar()
        super().save(*args, **kwargs)

    def process_avatar(self):
        if not self.avatar:
            return
        try:
            with Image.open(self.avatar) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail((300, 300))
                img.save(self.avatar.path, format='JPEG')
        except Exception as e:
            logger.error(f"Ошибка при обработке аватара: {e}", exc_info=True)

    def is_online(self):
        """
        Локальный метод проверки "онлайн" — можно вызвать в шаблоне: profile.is_online()
        Или использовать менеджер: Profile.objects.online()
        """
        return timezone.now() - self.last_activity <= self.ONLINE_THRESHOLD


# -----------------------------------------------------------------------
# Адреса
# -----------------------------------------------------------------------
class AddressQuerySet(models.QuerySet):
    def defaults(self):
        """Фильтр по адресам 'по умолчанию'."""
        return self.filter(is_default=True)


class AddressManager(models.Manager):
    def get_queryset(self):
        return AddressQuerySet(self.model, using=self._db)

    def default_for_user(self, user):
        """Удобный метод для получения дефолтного адреса конкретного пользователя."""
        return self.get_queryset().filter(user=user, is_default=True).first()


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    objects = AddressManager()

    def __str__(self):
        return f"{self.address_line1}, {self.city}, {self.country}"


# -----------------------------------------------------------------------
# Способы оплаты
# -----------------------------------------------------------------------
class PaymentMethodQuerySet(models.QuerySet):
    def default(self):
        """Возвращаем только способы оплаты, помеченные как is_default."""
        return self.filter(is_default=True)


class PaymentMethodManager(models.Manager):
    def get_queryset(self):
        return PaymentMethodQuerySet(self.model, using=self._db)

    def default_for_user(self, user):
        """Удобный метод для получения дефолтного способа оплаты конкретного пользователя."""
        return self.get_queryset().filter(user=user, is_default=True).first()


class PaymentMethod(models.Model):
    PAYMENT_TYPES = [
        ('credit_card', 'Кредитная карта'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Банковский перевод'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_methods")
    type = models.CharField(max_length=20, choices=PAYMENT_TYPES, verbose_name='Тип оплаты')
    details = models.CharField(max_length=255, verbose_name='Детали оплаты')
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    is_default = models.BooleanField(default=False)

    objects = PaymentMethodManager()

    def __str__(self):
        return f"{self.get_type_display()} ({self.user.username})"


# -----------------------------------------------------------------------
# Настройки уведомлений
# -----------------------------------------------------------------------
class NotificationSettingsManager(models.Manager):
    def for_user(self, user):
        """
        Удобный метод для получения/создания настроек уведомлений конкретного пользователя.
        """
        obj, created = self.get_or_create(user=user)
        return obj


class NotificationSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_settings")
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=False)

    objects = NotificationSettingsManager()

    def __str__(self):
        return f"Настройки уведомлений для {self.user.username}"


# -----------------------------------------------------------------------
# Активность пользователя (логи)
# -----------------------------------------------------------------------
class UserActivityQuerySet(models.QuerySet):
    def recent(self, user, limit=10):
        """
        Возвращает последние N событий для конкретного пользователя.
        """
        return self.filter(user=user).order_by('-timestamp')[:limit]


class UserActivityManager(models.Manager):
    def get_queryset(self):
        # Можно использовать select_related, если нужно
        return UserActivityQuerySet(self.model, using=self._db).select_related('user')

    def recent_for_user(self, user, limit=10):
        """
        Удобный метод для получения последних N событий по пользователю.
        """
        return self.get_queryset().recent(user, limit=limit)


class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=50)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    objects = UserActivityManager()

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} at {self.timestamp}"


# -----------------------------------------------------------------------
# Подписки (на категории)
# -----------------------------------------------------------------------
class SubscriptionQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user).select_related('category')


class SubscriptionManager(models.Manager):
    def get_queryset(self):
        # select_related(category) — если нужно часто брать поля категории
        return SubscriptionQuerySet(self.model, using=self._db).select_related('category')

    def for_user(self, user):
        """Удобный метод для получения подписок конкретного пользователя."""
        return self.get_queryset().for_user(user)


class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    category = models.ForeignKey('products.Category', on_delete=models.CASCADE)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    objects = SubscriptionManager()

    def __str__(self):
        return f"{self.user.username} подписан на {self.category.name}"


# -----------------------------------------------------------------------
# История логинов
# -----------------------------------------------------------------------
class UserLoginHistoryQuerySet(models.QuerySet):
    def last_login(self, user):
        """Возвращает последний по времени логин пользователя."""
        return (
            self.filter(user=user)
            .order_by('-login_datetime')
            .first()
        )


class UserLoginHistoryManager(models.Manager):
    def get_queryset(self):
        return UserLoginHistoryQuerySet(self.model, using=self._db).select_related('user')

    def last_login(self, user):
        """Удобный метод для получения последнего логина пользователя."""
        return self.get_queryset().last_login(user)


class UserLoginHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="login_history"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    session_key = models.CharField(max_length=128, blank=True)
    login_datetime = models.DateTimeField(auto_now_add=True)

    objects = UserLoginHistoryManager()

    class Meta:
        ordering = ('-login_datetime',)
        indexes = [
            models.Index(fields=['user', '-login_datetime']),
        ]

    def __str__(self):
        return f"{self.user} logged in at {self.login_datetime} from {self.ip_address}"


# -----------------------------------------------------------------------
# AdminSettings (Singleton)
# -----------------------------------------------------------------------
class AdminSettings(SingletonModel):
    site_logo = models.ImageField(upload_to='admin_logo/', blank=True, null=True, verbose_name='Логотип сайта')
    contact_email = models.EmailField(default='noreply@example.com', verbose_name='Контактный Email')
    site_timezone = models.CharField(
        max_length=32,
        choices=TIME_ZONE_CHOICES,
        default='UTC',
        verbose_name='Часовой пояс сайта'
    )
    welcome_message = models.TextField(
        default='Добро пожаловать в административную панель!',
        verbose_name='Приветственное сообщение'
    )

    def __str__(self):
        return "Настройки Административной Панели"

    class Meta:
        verbose_name = "Настройки Административной Панели"
