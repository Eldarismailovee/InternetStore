# Generated by Django 5.1.3 on 2024-12-09 23:14

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_userloginhistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentmethod',
            name='added_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Дата добавления'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='details',
            field=models.CharField(default=1, max_length=255, verbose_name='Детали оплаты'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='type',
            field=models.CharField(choices=[('credit_card', 'Кредитная карта'), ('paypal', 'PayPal'), ('bank_transfer', 'Банковский перевод')], default=1, max_length=20, verbose_name='Тип оплаты'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='profile',
            name='last_activity',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Последняя активность'),
        ),
    ]
