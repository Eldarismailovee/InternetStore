# accounts/admin.py

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.db.models import Count, Sum, Avg, F, FloatField, ExpressionWrapper
from django.utils.html import format_html
from django.utils import timezone
from django.core.cache import cache
from geopy import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import ipaddress
import pytz

from .models import (
    Profile,
    UserLoginHistory,
    Address,
    Subscription,
    PaymentMethod, AdminSettings,
)
from products.models import Order, Review, Wishlist

from solo.admin import SingletonModelAdmin  # Импортируем SingletonModelAdmin

User = get_user_model()

# Кортеж с выбором часовых поясов (опционально, если не используете django-timezone-field)
TIME_ZONE_CHOICES = tuple(zip(pytz.all_timezones, pytz.all_timezones))

class UserLoginHistoryInline(admin.TabularInline):
    model = UserLoginHistory
    fields = ('ip_address', 'user_agent', 'session_key', 'login_datetime', 'location_display')
    readonly_fields = ('ip_address', 'user_agent', 'session_key', 'login_datetime', 'location_display')
    extra = 0
    can_delete = False

    def location_display(self, obj):
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
            pass  # Некорректный IP, продолжаем попытку геокодирования

        cache_key = f"geolocation_{ip}"
        location = cache.get(cache_key)

        if not location:
            try:
                geolocator = Nominatim(user_agent="InternetStoreApp/1.0 (your-email@example.com)")
                location_result = geolocator.geocode(ip)
                if location_result:
                    location_str = f"{location_result.latitude}, {location_result.longitude}"
                else:
                    location_str = "Location not found"
                cache.set(cache_key, location_str, 60*60*24)  # Кэшировать на 1 день
                return location_str
            except GeocoderTimedOut:
                return "Geocoding timed out"
            except GeocoderUnavailable:
                return "Geocoding service unavailable"
            except Exception as e:
                return f"Error: {e}"
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
    max_num = 5  # Отображать до 5 заказов

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.max_num = self.max_num
        return formset

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')  # Без среза

class RecentReviewsInline(admin.TabularInline):
    model = Review
    fields = ('product', 'rating', 'comment', 'created_at')
    readonly_fields = ('product', 'rating', 'comment', 'created_at')
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "Последний отзыв"
    verbose_name_plural = "Последние отзывы"
    max_num = 5  # Отображать до 5 отзывов

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.max_num = self.max_num
        return formset

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')  # Без среза

class WishlistInline(admin.TabularInline):
    model = Wishlist
    fields = ('product', 'added_at')
    readonly_fields = ('product', 'added_at')
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "Список желаний"
    verbose_name_plural = "Списки желаний"
    max_num = 10  # Отображать до 10 товаров

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.max_num = self.max_num
        return formset

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
            return queryset.filter(profile__last_activity__gte=timezone.now() - Profile.ONLINE_THRESHOLD)
        if self.value() == 'offline':
            return queryset.filter(profile__last_activity__lt=timezone.now() - Profile.ONLINE_THRESHOLD)
        return queryset

class ProfileInline(admin.StackedInline):
    model = Profile
    fields = ('phone_number', 'time_zone', 'last_activity', 'receive_newsletters', 'receive_notifications')
    readonly_fields = ('last_activity',)
    can_delete = False
    verbose_name_plural = 'Profile'

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
        'user_login_info'
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
        ProfileInline  # Добавляем инлайн для Profile
    ]
    readonly_fields = ('last_login', 'date_joined', 'user_login_info', 'last_activity')

    def user_login_info(self, obj):
        # Отображение последнего IP и времени входа, если доступно
        latest_login = obj.login_history.first()
        if latest_login:
            return format_html(
                "<div><strong>IP:</strong> {}<br><strong>Last Login:</strong> {}</div>",
                latest_login.ip_address or "N/A", latest_login.login_datetime
            )
        return "Нет истории входов"
    user_login_info.short_description = "Информация о последнем входе"

    def order_count(self, obj):
        return obj.order_count
    order_count.short_description = 'Количество заказов'

    def total_spent(self, obj):
        return obj.total_spent
    total_spent.short_description = 'Общая сумма покупок'

    def average_wishlist_rating(self, obj):
        return obj.average_wishlist_rating
    average_wishlist_rating.short_description = 'Средний рейтинг в списке желаний'

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
        qs = super().get_queryset(request).select_related('profile').prefetch_related(
            'orders__items',
            'wishlist__product__reviews',
            'wishlist__product__category',  # Если необходимо
            'wishlist__product__related_products',  # Если необходимо
            'payment_methods',  # Если существует
        )
        # Вычисляем общую сумму покупок
        total_spent_expression = ExpressionWrapper(
            F('orders__items__price') * F('orders__items__quantity'),
            output_field=FloatField()
        )
        qs = qs.annotate(
            order_count=Count('orders', distinct=True),
            total_spent=Sum(total_spent_expression),
            average_wishlist_rating=Avg('wishlist__product__reviews__rating')
        )
        return qs

    def get_urls(self):
        from django.urls import path
        from .admin_views import preview_homepage

        urls = super().get_urls()
        custom_urls = [
            path('preview-homepage/', self.admin_site.admin_view(preview_homepage), name='preview_homepage'),
        ]
        return custom_urls + urls

# Отменяем регистрацию стандартного UserAdmin
admin.site.unregister(User)

# Регистрируем User с CustomUserAdmin
admin.site.register(User, CustomUserAdmin)

# Регистрация модели AdminSettings
class AdminSettingsAdmin(SingletonModelAdmin):
    """
    Админ-класс для модели AdminSettings.
    """
    fieldsets = (
        (None, {
            'fields': ('site_logo', 'contact_email', 'site_timezone', 'welcome_message')
        }),
    )
    # Добавьте поиск или фильтры, если необходимо

admin.site.register(AdminSettings, AdminSettingsAdmin)  # Регистрация модели настроек
