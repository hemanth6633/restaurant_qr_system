# Generated by Django 4.2 on 2024-12-17 14:38

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant_app', '0007_bill_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='waiterreview',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]