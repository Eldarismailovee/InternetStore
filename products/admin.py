# admin.py
from django.contrib import admin
from django.db.models import Sum, F
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from imagekit.admin import AdminThumbnail

from .models import Product, Category, OrderItem, Order, StaticPage, SubCategory


class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1
    fields = ('name', 'slug', 'icon')
    prepopulated_fields = {'slug': ('name',)}


class ProductInline(admin.TabularInline):
    model = Product
    extra = 1
    fields = ('name', 'price', 'stock')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SubCategoryInline, ProductInline]
    ordering = ['name']


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'icon')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('category',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    admin_thumbnail = AdminThumbnail(image_field='image_thumbnail')
    list_display = (
        'name', 'price', 'admin_thumbnail', 'price_with_currency', 'category',
        'is_featured', 'stock', 'created_at', 'image_tag'
    )
    list_editable = ('price', 'is_featured', 'stock')
    list_filter = ('is_featured', 'category', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    save_on_top = True
    list_per_page = 20
    filter_horizontal = ('related_products',)
    readonly_fields = ('image_preview', 'price_with_currency')
    fieldsets = (
        (None, {
            'fields': (('name', 'slug'), 'category', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'price_with_currency')
        }),
        ('Stock & Features', {
            'fields': ('stock', 'is_featured')
        }),
        ('Images', {
            'fields': ('image', 'image_preview')
        }),
    )
    autocomplete_fields = ['category']

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(
                '<img src="{}" style="max-width: 300px; max-height: 300px;" />'.format(obj.image.url)
            )
        return "Нет изображения"
    image_preview.short_description = 'Предпросмотр изображения'

    def image_tag(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 50px; max-height: 50px;" />', obj.image.url
            )
        return '-'
    image_tag.short_description = 'Изображение'

    def price_with_currency(self, obj):
        return f"{obj.price} руб."
    price_with_currency.short_description = 'Цена (с валютой)'
    price_with_currency.admin_order_field = 'price'

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm('app.delete_product')

    @admin.action(description='Пометить выбранные продукты как "На главной"')
    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description='Пометить выбранные продукты как "Не на главной"')
    def make_not_featured(self, request, queryset):
        queryset.update(is_featured=False)

    actions = ['make_featured', 'make_not_featured']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'paid', 'total_amount']
    ordering = ['-created_at']
    list_filter = ['paid', 'created_at']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'user']
    autocomplete_fields = ['user']
    list_select_related = ('user',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            total_amount=Sum(F('items__price') * F('items__quantity')))

    def total_amount(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())
    total_amount.short_description = 'Общая сумма'


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'updated_at', 'preview_link')
    search_fields = ('title', 'slug', 'content')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('updated_at',)
    readonly_fields = ('preview', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'content', 'updated_at', 'preview')
        }),
    )

    def preview_link(self, obj):
        if obj.pk:
            url = reverse('products:staticpage_preview', args=[obj.pk])
            return format_html('<a href="{}" target="_blank">Предпросмотр</a>', url)
        return "-"
    preview_link.short_description = "Предпросмотр"

    def preview(self, obj):
        if obj.pk:
            url = reverse('products:staticpage_preview', args=[obj.pk])
            return format_html('<a href="{}" target="_blank">Открыть Предпросмотр</a>', url)
        return "-"
    preview.short_description = "Предпросмотр"
