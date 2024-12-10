from django.shortcuts import render

from products.models import Product

def home(request):
    featured_products = Product.objects.filter(is_featured=True)
    context = {
        'featured_products': featured_products,
    }
    return render(request, 'home.html', context)


def home_view(request):
    return render(request, 'home.html')


def about(request):
    return render(request, 'about.html')


def contact(request):
    return render(request,'contact.html')