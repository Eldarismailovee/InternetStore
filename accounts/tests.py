# accounts/tests/test_admin.py

from unittest.mock import patch, MagicMock

from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from accounts.admin import CustomUserAdmin
from accounts.models import (
    Profile,
    UserLoginHistory,
    AdminSettings,
)
from products.models import Order, OrderItem, Product, Category, Review, Wishlist

User = get_user_model()


class CustomUserAdminTests(TestCase):
    """Тесты для кастомного UserAdmin (CustomUserAdmin)."""

    @classmethod
    def setUpTestData(cls):
        # Создадим суперпользователя и обычного пользователя
        cls.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass"
        )
        cls.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="12345"
        )
        # Создаем профиль, связанный с пользователем
        cls.profile = Profile.objects.get(user=cls.user)  # т.к. создаётся сигналом post_save

        # Создаём категорию и продукты для wishlist и отзывов
        cls.category = Category.objects.create(name="TestCategory")
        cls.product_1 = Product.objects.create(name="Test Product 1", price=100, category=cls.category)
        cls.product_2 = Product.objects.create(name="Test Product 2", price=200, category=cls.category)

        # Создаем заказ, в котором есть OrderItem (для подсчета total_spent)
        cls.order = Order.objects.create(user=cls.user, status="created")
        OrderItem.objects.create(order=cls.order, product=cls.product_1, price=cls.product_1.price, quantity=2)

        # Создаём wishlist
        Wishlist.objects.create(user=cls.user, product=cls.product_1)
        Wishlist.objects.create(user=cls.user, product=cls.product_2)

        # Создаём несколько отзывов, чтобы проверить средний рейтинг
        Review.objects.create(user=cls.user, product=cls.product_1, rating=4, comment="Good product!")
        Review.objects.create(user=cls.user, product=cls.product_2, rating=5, comment="Excellent product!")

    def setUp(self):
        """Подключаем клиент и логинимся под суперпользователем, чтобы иметь доступ в админку."""
        self.client = Client()
        self.client.login(username="admin", password="adminpass")

    def test_admin_registration(self):
        """
        Проверяем, что дефолтный UserAdmin снят с регистрации
        и зарегистрирован CustomUserAdmin.
        """
        # Получаем модель User через get_user_model()
        user_model = User
        # Проверяем, что в admin.site зарегистрирован именно CustomUserAdmin для модели User
        self.assertIsInstance(site._registry[user_model], CustomUserAdmin)

    def test_changelist_loads(self):
        """
        Проверяем, что список пользователей в админке (changelist) открывается без ошибок.
        """
        url = reverse("admin:auth_user_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "testuser")  # Убеждаемся, что наш пользователь виден

    def test_annotations_in_changelist(self):
        """
        Проверяем, что кастомные аннотированные поля (order_count, total_spent, average_wishlist_rating)
        корректно отображаются в списке.
        """
        url = reverse("admin:auth_user_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Ищем в HTML наш тестовый username и числовые значения, соответствующие аннотациям
        self.assertContains(response, "testuser")
        # Количество заказов
        self.assertContains(response, ">1<", msg_prefix="Проверяем, что order_count = 1")
        # Общая сумма (2 * 100) = 200.0
        self.assertContains(response, ">200.0<", msg_prefix="Проверяем, что total_spent = 200.0")
        # Средний рейтинг товаров в wishlist: (4 + 5) / 2 = 4.5
        self.assertContains(response, ">4.5<", msg_prefix="Проверяем, что average_wishlist_rating = 4.5")

    def test_online_filter(self):
        """
        Проверяем работу фильтра по онлайн-статусу (OnlineFilter).
        """
        # Установим last_activity так, чтобы пользователь считался онлайн.
        self.profile.last_activity = timezone.now()
        self.profile.save()

        changelist_url = reverse("admin:auth_user_changelist") + "?is_online=online"
        response = self.client.get(changelist_url)
        self.assertEqual(response.status_code, 200)
        # Проверяем, что наш testuser в списке
        self.assertContains(response, "testuser")

        # Теперь сделаем last_activity "давней" - пользователь будет оффлайн
        self.profile.last_activity = timezone.now() - (Profile.ONLINE_THRESHOLD + timezone.timedelta(minutes=5))
        self.profile.save()

        changelist_url = reverse("admin:auth_user_changelist") + "?is_online=online"
        response = self.client.get(changelist_url)
        self.assertNotContains(response, "testuser", msg_prefix="Пользователь должен исчезнуть из фильтра 'online'")

        # Проверим фильтр на 'offline'
        changelist_url = reverse("admin:auth_user_changelist") + "?is_online=offline"
        response = self.client.get(changelist_url)
        self.assertContains(response, "testuser", msg_prefix="Пользователь должен появиться в фильтре 'offline'")

    def test_user_login_history_inline_display(self):
        """
        Проверяем, что inline для истории логинов отображается корректно
        и что метод user_login_info выводит ожидаемую информацию.
        """
        # Создаём запись истории логина
        UserLoginHistory.objects.create(
            user=self.user,
            ip_address="127.0.0.1",
            user_agent="TestAgent",
            session_key="abc123"
        )

        url = reverse("admin:auth_user_change", args=[self.user.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Ищем поля в inline
        self.assertContains(response, "TestAgent")
        self.assertContains(response, "127.0.0.1")

        # Проверяем user_login_info (в list_display) через changelist
        changelist_url = reverse("admin:auth_user_changelist")
        response = self.client.get(changelist_url)
        self.assertContains(response, "IP:")
        self.assertContains(response, "Last Login:")

    @patch("accounts.admin.Nominatim")
    def test_location_display(self, mock_nominatim):
        """
        Проверяем, что location_display корректно возвращает "Localhost", "Private IP" или "Location not found".
        Для внешних IP-адресов используем mock, чтобы не вызывать реальный сервис.
        """
        history = UserLoginHistory.objects.create(
            user=self.user,
            ip_address="127.0.0.1",
            user_agent="Mozilla",
            session_key="testsession"
        )

        # Проверяем отображение для "127.0.0.1" => Localhost
        url = reverse("admin:auth_user_change", args=[self.user.pk])
        response = self.client.get(url)
        self.assertContains(response, "Localhost")

        # Меняем IP на приватный
        history.ip_address = "192.168.0.10"
        history.save()
        response = self.client.get(url)
        self.assertContains(response, "Private IP")

        # Меняем IP на внешний
        history.ip_address = "8.8.8.8"
        history.save()

        # Настраиваем mock-ответ от geocode
        instance = mock_nominatim.return_value
        instance.geocode.return_value = MagicMock(latitude=55.7558, longitude=37.6176)

        response = self.client.get(url)
        self.assertContains(response, "55.7558, 37.6176")

        # Проверим ситуацию, когда geocode вернул None => Location not found
        instance.geocode.return_value = None
        # Нужно очистить кэш или изменить IP, чтобы повторно вызвать geocoder
        history.ip_address = "8.8.4.4"
        history.save()

        response = self.client.get(url)
        self.assertContains(response, "Location not found")

    def test_custom_url_preview_homepage(self):
        """
        Проверяем, что кастомный URL (preview_homepage) доступен и редиректит на '/'
        (или другую страницу, указанную в коде).
        """
        preview_url = reverse("admin:preview_homepage")
        response = self.client.get(preview_url)
        # Должен быть редирект, по умолчанию HttpResponseRedirect => 302
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.url)


class AdminSettingsAdminTests(TestCase):
    """Тесты для AdminSettingsAdmin (SingletonModel)."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass"
        )

    def setUp(self):
        self.client = Client()
        self.client.login(username="admin", password="adminpass")

    def test_admin_settings_admin(self):
        """
        Проверяем, что AdminSettings корректно отображается в админке и можно зайти на форму редактирования.
        """
        # Создадим объект настроек (Singleton)
        settings_obj = AdminSettings.get_solo()
        self.assertIsNotNone(settings_obj)

        # Список объектов в админке (по сути 1 объект)
        url = reverse("admin:accounts_adminsettings_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Заходим на форму редактирования
        change_url = reverse("admin:accounts_adminsettings_change", args=[settings_obj.id])
        response = self.client.get(change_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Настройки Административной Панели")
        self.assertContains(response, "Приветственное сообщение")
