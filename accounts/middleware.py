# accounts/middleware.py

from django.utils import timezone
import pytz


class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Установка часового пояса
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile and profile.time_zone:
                try:
                    timezone.activate(pytz.timezone(profile.time_zone))
                except pytz.UnknownTimeZoneError:
                    timezone.deactivate()
            else:
                timezone.deactivate()

        # Обновление last_activity
        response = self.get_response(request)
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile:
                profile.last_activity = timezone.now()
                profile.save(update_fields=['last_activity'])
        return response
