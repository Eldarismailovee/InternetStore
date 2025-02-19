# Generated by Django 5.1.3 on 2024-11-13 09:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название категории')),
                ('icon', models.CharField(help_text='CSS-класс иконки Font Awesome', max_length=50, verbose_name='Иконка')),
            ],
        ),
    ]
