from django.core.cache import cache
from .forms import UserLoginForm, UserRegisterForm
from .models import AdminSettings


def auth_forms(request):
    """Передача форм аутентификации только для определенных URL"""
    if request.path in ('/login/', '/register/'):
        return {
            'login_form': UserLoginForm(),
            'register_form': UserRegisterForm()
        }
    return {}


def admin_settings(request):
    """Кешированные настройки админки для всех шаблонов"""
    cache_key = 'admin_settings'
    settings = cache.get(cache_key)

    if not settings:
        try:
            settings = AdminSettings.get_solo()
            cache.set(cache_key, settings, 60 * 60 * 24)  # Кеш на 24 часа
        except Exception as e:
            settings = None

    return {'admin_settings': settings or AdminSettings()}