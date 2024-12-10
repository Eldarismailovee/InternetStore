# accounts/context_processors.py

from .forms import UserLoginForm, UserRegisterForm
from .models import AdminSettings


def auth_forms(request):
    return {
        'login_form': UserLoginForm(),
        'register_form': UserRegisterForm(),
    }

def admin_settings(request):
    """
    Контекст-процессор для передачи настроек админки в шаблоны.
    """
    return {
        'admin_settings': AdminSettings.objects.first()  # Используйте get_solo() если используете django-solo
    }