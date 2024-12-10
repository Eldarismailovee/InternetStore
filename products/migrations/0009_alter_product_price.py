# Generated by Django 5.1.3 on 2024-11-16 15:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0008_review_wishlist'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(db_index=True, decimal_places=2, max_digits=10, verbose_name='Цена'),
        ),
    ]