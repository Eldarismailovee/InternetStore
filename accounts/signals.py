# accounts/signals.py

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile, UserLoginHistory
from .utils import get_client_ip  # Предполагается, что у вас есть утилита для получения IP

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

# Если у вас есть сигнал для логинов, убедитесь, что он принимает **kwargs
from django.contrib.auth.signals import user_logged_in

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    UserLoginHistory.objects.create(
        user=user,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        session_key=request.session.session_key
    )
