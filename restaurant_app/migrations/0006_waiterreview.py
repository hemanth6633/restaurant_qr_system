# Generated by Django 4.2 on 2024-12-15 05:35

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant_app', '0005_remove_tip_bill_remove_tip_payment_method_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='WaiterReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tip', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='restaurant_app.tip')),
                ('waiter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='restaurant_app.waiter')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]