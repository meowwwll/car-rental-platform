# Generated by Django 4.2.1 on 2025-05-11 11:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_carrentalrequest_is_unlocked'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='userprofile',
            constraint=models.UniqueConstraint(fields=('driver_license_series', 'driver_license_number'), name='unique_driver_license'),
        ),
    ]
