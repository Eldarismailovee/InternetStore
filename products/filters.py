# products/filters.py

import django_filters
from .models import Product, Category

class ProductFilter(django_filters.FilterSet):
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte', label='Цена от')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte', label='Цена до')
    category = django_filters.ModelChoiceFilter(queryset=Category.objects.all(), label='Категория')

    ordering = django_filters.OrderingFilter(
        choices=(
            ('price', 'По возрастанию цены'),
            ('-price', 'По убыванию цены'),
            ('name', 'По названию (А-Я)'),
            ('-name', 'По названию (Я-А)'),
        ),
        label='Сортировка'
    )

    class Meta:
        model = Product
        fields = ['category', 'price_min', 'price_max']
