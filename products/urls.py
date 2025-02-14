# products/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'products'  # Пространство имён

urlpatterns = [
    path('', views.home, name='home'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('order/create/', views.order_create, name='order_create'),

    path('category/<slug:slug>/', views.category_detail, name='category_detail'),

    path('search/', views.product_search, name='product_search'),

    path('product/<int:product_id>/add_review/', views.add_review, name='add_review'),

    path('orders/history/', views.order_history, name='order_history'),

    # Исправленная строка для wishlist
    path('wishlist/', views.view_wishlist, name='view_wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    path('products/', views.ProductListView.as_view(), name='product_list'),

    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='accounts/password_change.html'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='accounts/password_change_done.html'), name='password_change_done'),

    path('cart/update_quantity/', views.update_quantity, name='update_quantity'),
    path('cart/remove_item/', views.remove_item, name='remove_item'),
    path('staticpage/<int:pk>/preview/', views.static_page_preview, name='staticpage_preview'),
    path('category/<slug:category_slug>/<slug:subcategory_slug>/', views.subcategory_detail, name='subcategory_detail'),

    path('search_suggestions/', views.search_suggestions, name='search_suggestions'),
]
