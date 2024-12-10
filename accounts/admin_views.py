# accounts/admin_views.py

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponseRedirect

@staff_member_required
def preview_homepage(request):
    """
    Представление для предпросмотра главной страницы.
    """
    return HttpResponseRedirect(reverse('home'))  # Замените 'home' на имя вашего URL главной страницы
