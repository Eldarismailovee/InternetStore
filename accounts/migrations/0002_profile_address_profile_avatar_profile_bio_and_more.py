# Generated by Django 5.1.3 on 2024-11-16 08:38

import accounts.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='address',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='profile',
            name='avatar',
            field=models.ImageField(blank=True, default='default_avatar.jpg', upload_to=accounts.models.user_directory_path),
        ),
        migrations.AddField(
            model_name='profile',
            name='bio',
            field=models.TextField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='profile',
            name='birth_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='phone_number',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
