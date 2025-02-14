from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.core.exceptions import ObjectDoesNotExist
from .models import Profile, UserLoginHistory
from .utils import get_client_ip
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Создание профиля при регистрации нового пользователя"""
    if created:
        try:
            Profile.objects.create(user=instance)
            logger.info(f"Создан профиль для пользователя {instance.username}")
        except Exception as e:
            logger.error(f"Ошибка создания профиля: {e}", exc_info=True)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Обновление профиля при изменении пользователя"""
    try:
        instance.profile.save()
    except ObjectDoesNotExist:
        logger.warning(f"Профиль для {instance.username} не найден, создаем...")
        Profile.objects.create(user=instance)
    except Exception as e:
        logger.error(f"Ошибка сохранения профиля: {e}", exc_info=True)

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Логирование успешного входа в систему"""
    try:
        UserLoginHistory.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
            session_key=request.session.session_key or ''
        )
    except Exception as e:
        logger.error(f"Ошибка логирования входа: {e}", exc_info=True)