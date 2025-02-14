# utils.py
from django.core.cache import cache
from ipware import get_client_ip


def get_client_ip(request):
    cache_key=f"client_ip_{request.session.session_key}"
    ip=cache.get(cache_key)
    if not ip:
        ip, _ = get_client_ip(request)
        cache.set(cache_key,ip,60*5)

    return ip or ''