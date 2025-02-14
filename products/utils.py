# utils.py (пример вспомогательной функции для fuzzy search)
import difflib


def fuzzy_search_suggestions(query):
    # Пример упрощённой логики:
    # Допустим, у нас есть список всех имен продуктов.
    # Используем difflib.get_close_matches для получения близких совпадений.
    from .models import Product
    all_names = Product.objects.values_list('name', flat=True)
    suggestions = difflib.get_close_matches(query, all_names, n=5, cutoff=0.6)
    return suggestions
