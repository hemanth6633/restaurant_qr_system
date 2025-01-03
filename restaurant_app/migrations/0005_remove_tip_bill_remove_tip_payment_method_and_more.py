# Generated by Django 4.2 on 2024-12-07 14:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant_app', '0004_feedback'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tip',
            name='bill',
        ),
        migrations.RemoveField(
            model_name='tip',
            name='payment_method',
        ),
        migrations.AddField(
            model_name='waiter',
            name='bank_account_name',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='waiter',
            name='bank_account_number',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='waiter',
            name='bank_ifsc_code',
            field=models.CharField(blank=True, max_length=11),
        ),
        migrations.AddField(
            model_name='waiter',
            name='upi_id',
            field=models.CharField(blank=True, help_text='UPI ID for receiving tips', max_length=50),
        ),
        migrations.AlterField(
            model_name='tip',
            name='payment_status',
            field=models.CharField(choices=[('PENDING', 'Pending'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')], default='PENDING', max_length=20),
        ),
        migrations.AlterField(
            model_name='tip',
            name='reference_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='tip',
            name='waiter',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tips', to='restaurant_app.waiter'),
        ),
    ]
