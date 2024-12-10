from datetime import datetime

from .cart import Cart

def cart_total_amount(request):
    cart = Cart(request)
    return {'cart_total_items': len(cart)}

def current_year(request):
    return {'current_year': datetime.now().year}
