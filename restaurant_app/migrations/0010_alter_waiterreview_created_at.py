# Generated by Django 4.2 on 2024-12-18 04:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('restaurant_app', '0009_alter_waiterreview_created_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='waiterreview',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
