# InternetMagazin/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from products import views as product_views
from . import views
urlpatterns = [
    path('grappelli/', include('grappelli.urls')),  # Если используете Grappelli
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('admin/', admin.site.urls),

    path('', product_views.home, name='home'),
    path('', include('products.urls', namespace='products')),
    path('', views.home_view, name='home'),
    path('ckeditor5/', include('django_ckeditor_5.urls')),  # Если используете CKEditor5
  #  path('two_factor/', include(('two_factor.urls', 'two_factor'), namespace='two_factor')),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)