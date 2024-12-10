# accounts/views.py

from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Avg
from django.shortcuts import redirect, render, get_object_or_404

from accounts.models import Address, NotificationSettings, Subscription, UserLoginHistory
from products.models import Order, Wishlist, Product, Review
from .forms import UserRegisterForm, UserForm, ProfileForm, AddressForm, NotificationSettingsForm, SubscriptionForm
from .utils import get_client_ip


def register(request):
    """
    Представление для регистрации нового пользователя.
    """
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()  # UserCreationForm автоматически хеширует пароль
            login(request, user)
            messages.success(request, 'Вы успешно зарегистрировались!')
            return redirect('home')  # Убедитесь, что у вас есть маршрут 'home'
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = UserRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})
@login_required
def profile(request):
    """
    Представление для отображения профиля пользователя.
    """
    average_rating = Review.objects.filter(product__in=Wishlist.objects.filter(user=request.user).values('product')).aggregate(Avg('rating'))['rating__avg']
    context = {
        'average_rating': average_rating,
    }
    return render(request, 'accounts/profile.html', context)
@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(
            request.POST,
            request.FILES,
            instance=request.user.profile
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Профиль успешно обновлён.')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)
    return render(request, 'accounts/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })
@login_required
def order_history(request):
    """
    Представление для отображения истории заказов пользователя.
    """
    orders = Order.objects.filter(user=request.user).select_related('user').prefetch_related('items__product').order_by('-created_at')
    return render(request, 'accounts/order_history.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    """
    Представление для отображения деталей конкретного заказа.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'accounts/order_detail.html', {'order': order})

@login_required
def wishlist(request):
    """
    Представление для отображения списка желаний пользователя.
    """
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'accounts/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def add_to_wishlist(request, product_id):
    """
    Представление для добавления товара в список желаний.
    """
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if created:
        messages.success(request, 'Товар добавлен в список желаний.')
    else:
        messages.info(request, 'Товар уже в вашем списке желаний.')
    return redirect('products:product_detail', product_id=product.id)

@login_required
def remove_from_wishlist(request, product_id):
    """
    Представление для удаления товара из списка желаний.
    """
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.success(request, 'Товар удалён из списка желаний.')
    return redirect('accounts:wishlist')

@login_required
def manage_addresses(request):
    addresses = request.user.addresses.all()
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            if address.is_default:
                # Сбросить предыдущие адреса по умолчанию
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
            address.save()
            messages.success(request, 'Адрес успешно добавлен.')
            return redirect('accounts:manage_addresses')
    else:
        form = AddressForm()
    return render(request, 'accounts/manage_addresses.html', {'addresses': addresses, 'form': form})

@login_required
def notification_settings(request):
    settings, created = NotificationSettings.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = NotificationSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки уведомлений обновлены.')
            return redirect('accounts:notification_settings')
    else:
        form = NotificationSettingsForm(instance=settings)
    return render(request, 'accounts/notification_settings.html', {'form': form})

@login_required
def activity_history(request):
    activities = request.user.activities.all().order_by('-timestamp')
    return render(request, 'accounts/activity_history.html', {'activities': activities})

@login_required
def manage_subscriptions(request):
    subscriptions = request.user.subscriptions.select_related('category').all()
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.user = request.user
            subscription.save()
            messages.success(request, f"Подписка на {subscription.category.name} добавлена.")
            return redirect('accounts:manage_subscriptions')
    else:
        form = SubscriptionForm()
    return render(request, 'accounts/manage_subscriptions.html', {'subscriptions': subscriptions, 'form': form})

# accounts/views.py

@login_required
def unsubscribe(request, subscription_id):
    subscription = get_object_or_404(Subscription, id=subscription_id, user=request.user)
    if request.method == 'POST':
        subscription.delete()
        messages.success(request, f"Вы отписались от {subscription.category.name}.")
    return redirect('accounts:manage_subscriptions')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            UserLoginHistory.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_key=request.session.session_key
            )
            return redirect('home')  # После успешного логина перенаправление
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

