import logging
import ipaddress
from zoneinfo import available_timezones  # Для формирования списка часовых поясов

import requests
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.db.models import Count, Sum, Avg, F, FloatField, ExpressionWrapper
from django.utils.html import format_html
from django.utils import timezone
from django.core.cache import cache

from geopy import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from solo.admin import SingletonModelAdmin

from .models import (
    Profile,
    UserLoginHistory,
    Address,
    Subscription,
    PaymentMethod,
    AdminSettings,
)
from products.models import Order, Review, Wishlist

User = get_user_model()
logger = logging.getLogger(__name__)

TIME_ZONE_CHOICES = [(tz, tz) for tz in sorted(available_timezones())]

# --- Inlines ---

class UserLoginHistoryInline(admin.TabularInline):
    model = UserLoginHistory
    fields = ('ip_address', 'user_agent', 'session_key', 'login_datetime', 'location_display')
    readonly_fields = ('ip_address', 'user_agent', 'session_key', 'login_datetime', 'location_display')
    extra = 0
    can_delete = False

    def location_display(self, obj):
        """
        Попытка получить геолокацию по IP через Nominatim (OpenStreetMap).
        Результат кешируется на 24 часа.
        """
        ip = obj.ip_address

        # Проверка на localhost
        if ip.startswith('127.') or ip == '::1':
            return "Localhost"

        # Проверка на приватный IP
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private:
                return "Private IP"
        except ValueError:
            pass  # Некорректный IP, продолжаем

        cache_key = f"geolocation_{ip}"
        location = cache.get(cache_key)

        if not location:
            try:
                response = requests.get(f"http://ip-api.com/json/{ip}?fields=lat,lon")
                if response.status_code == 200:
                    data = response.json()
                    location_str = f"{data['lat']}, {data['lon']}"
            except Exception as e:
                logger.error(f"Geocoding error: {e}")
                return "Geocoding error"

        return location

    location_display.short_description = "User Location"


class AddressInline(admin.TabularInline):
    model = Address
    fields = ('address_line1', 'address_line2', 'city', 'postal_code', 'country', 'is_default')
    readonly_fields = ('address_line1', 'city', 'country', 'is_default')
    extra = 0
    can_delete = False


class SubscriptionInline(admin.TabularInline):
    model = Subscription
    fields = ('category', 'subscribed_at')
    readonly_fields = ('category', 'subscribed_at')
    extra = 0
    can_delete = False


class PaymentMethodInline(admin.TabularInline):
    model = PaymentMethod
    fields = ('type', 'details', 'added_at')
    readonly_fields = ('type', 'details', 'added_at')
    extra = 0
    can_delete = False


class RecentOrdersInline(admin.TabularInline):
    model = Order
    fields = ('id', 'address', 'postal_code', 'city', 'created_at', 'paid', 'status')
    readonly_fields = ('id', 'address', 'postal_code', 'city', 'created_at', 'paid', 'status')
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "Последний заказ"
    verbose_name_plural = "Последние заказы"
    max_num = 5

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')


class RecentReviewsInline(admin.TabularInline):
    model = Review
    fields = ('product', 'rating', 'comment', 'created_at')
    readonly_fields = ('product', 'rating', 'comment', 'created_at')
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "Последний отзыв"
    verbose_name_plural = "Последние отзывы"
    max_num = 5

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')


class WishlistInline(admin.TabularInline):
    model = Wishlist
    fields = ('product', 'added_at')
    readonly_fields = ('product', 'added_at')
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "Список желаний"
    verbose_name_plural = "Списки желаний"
    max_num = 10

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-added_at')


# --- Фильтр "Онлайн / Оффлайн" ---

class OnlineFilter(admin.SimpleListFilter):
    title = 'Статус пользователя'
    parameter_name = 'is_online'

    def lookups(self, request, model_admin):
        return (
            ('online', 'Онлайн'),
            ('offline', 'Оффлайн'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'online':
            return queryset.filter(
                profile__last_activity__gte=timezone.now() - Profile.ONLINE_THRESHOLD
            )
        if self.value() == 'offline':
            return queryset.filter(
                profile__last_activity__lt=timezone.now() - Profile.ONLINE_THRESHOLD
            )
        return queryset


class ProfileInline(admin.StackedInline):
    model = Profile
    fields = ('phone_number', 'time_zone', 'last_activity', 'receive_newsletters', 'receive_notifications')
    readonly_fields = ('last_activity',)
    can_delete = False
    verbose_name_plural = 'Profile'


# --- Кастомный UserAdmin ---

class CustomUserAdmin(DefaultUserAdmin):
    list_display = (
        'username',
        'email',
        'order_count',
        'total_spent',
        'average_wishlist_rating',
        'is_online',
        'last_activity',
        'last_login',
        'date_joined',
        'user_login_info',
    )
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', OnlineFilter)
    filter_horizontal = ('groups', 'user_permissions',)
    inlines = [
        UserLoginHistoryInline,
        AddressInline,
        SubscriptionInline,
        PaymentMethodInline,
        RecentOrdersInline,
        RecentReviewsInline,
        WishlistInline,
        ProfileInline,
    ]
    readonly_fields = ('last_login', 'date_joined', 'user_login_info', 'last_activity')

    def user_login_info(self, obj):
        latest_login = obj.login_history.first()
        if latest_login:
            return format_html(
                "<div><strong>IP:</strong> {}<br><strong>Last Login:</strong> {}</div>",
                latest_login.ip_address or "N/A",
                latest_login.login_datetime
            )
        return "Нет истории входов"
    user_login_info.short_description = "Информация о последнем входе"

    def order_count(self, obj):
        return obj.order_count or 0
    order_count.short_description = 'Количество заказов'
    order_count.admin_order_field = 'order_count'

    def total_spent(self, obj):
        return round(obj.total_spent or 0, 2)
    total_spent.short_description = 'Общая сумма покупок'
    total_spent.admin_order_field = 'total_spent'

    def average_wishlist_rating(self, obj):
        if obj.average_wishlist_rating is None:
            return "-"
        return round(obj.average_wishlist_rating, 2)
    average_wishlist_rating.short_description = 'Средний рейтинг в списке желаний'
    average_wishlist_rating.admin_order_field = 'average_wishlist_rating'

    def is_online(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile:
            return "Онлайн" if profile.is_online() else "Оффлайн"
        return "Неизвестно"
    is_online.short_description = 'Статус пользователя'

    def last_activity(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile:
            return profile.last_activity if not profile.is_online() else "Сейчас"
        return "Неизвестно"
    last_activity.short_description = 'Последняя активность'

    def get_queryset(self, request):
        """
        Кешируем аннотированный QuerySet при отсутствии фильтров (GET-параметров).
        При наличии параметров (поиск, фильтр) — используем «живые» данные без кеша,
        чтобы не ломать пагинацию и фильтрацию.
        """
        # Генерируем уникальный ключ на основе параметров поиска/фильтра
        cache_key = f"admin_user_qs:{request.GET.urlencode()}"
        cached_qs = cache.get(cache_key)
        if cached_qs:
            return cached_qs

        qs = super().get_queryset(request).select_related('profile').prefetch_related(
            'orders__items',
            'wishlist__product__reviews',
            'wishlist__product__category',
            'wishlist__product__related_products',
            'payment_methods',
        )

        total_spent_expression = ExpressionWrapper(
            F('orders__items__price') * F('orders__items__quantity'),
            output_field=FloatField()
        )
        qs = qs.annotate(
            order_count=Count('orders', distinct=True),
            total_spent=Sum(total_spent_expression),
            average_wishlist_rating=Avg('wishlist__product__reviews__rating'),
        )

        # Можно задать TTL или оставить до перезаписи при следующих фильтрах
        cache.set(cache_key, qs, 300)  # например, 5 минут
        return qs

    def get_urls(self):
        from django.urls import path
        # Пример — если у вас есть .admin_views с таким методом
        from .admin_views import preview_homepage

        urls = super().get_urls()
        custom_urls = [
            path('preview-homepage/', self.admin_site.admin_view(preview_homepage), name='preview_homepage'),
        ]
        return custom_urls + urls


# Убираем стандартный UserAdmin, регистрируем свой
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# --- AdminSettings ---

class AdminSettingsAdmin(SingletonModelAdmin):
    """
    Кеширование настроек сайта. При сохранении сбрасываем/обновляем кеш.
    """
    fieldsets = (
        (None, {
            'fields': ('site_logo', 'contact_email', 'site_timezone', 'welcome_message')
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        При сохранении экземпляра AdminSettings — обновляем кеш.
        """
        super().save_model(request, obj, form, change)
        # Сохраняем объект в кеш (можно и отдельные поля)
        cache.set('admin_settings', obj, 60 * 60 * 24)  # 24 часа

admin.site.register(AdminSettings, AdminSettingsAdmin)
