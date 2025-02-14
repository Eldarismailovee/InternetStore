# accounts/middleware.py
from django.conf import settings
from django.utils import timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import logging

from accounts.models import Profile

logger = logging.getLogger(__name__)

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
                if profile.time_zone:
                    timezone.activate(ZoneInfo(profile.time_zone))
                else:
                    timezone.deactivate()
            except (Profile.DoesNotExist, AttributeError, ZoneInfoNotFoundError) as e:
                timezone.deactivate()
                logger.warning(f"Timezone error for user {request.user}: {e}")
            except ZoneInfoNotFoundError:
                timezone.activate(settings.TIME_ZONE)
        else:
            timezone.deactivate()

        return self.get_response(request)

class LastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            # Оптимизированный запрос без загрузки объекта
            Profile.objects.filter(user=request.user).update(
                last_activity=timezone.now()
            )

        return response