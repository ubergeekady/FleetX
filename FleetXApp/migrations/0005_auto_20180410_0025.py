# Generated by Django 2.0.3 on 2018-04-10 00:25

from django.db import migrations
import timezone_field.fields


class Migration(migrations.Migration):

    dependencies = [
        ('FleetXApp', '0004_auto_20180409_2333'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='timezone',
            field=timezone_field.fields.TimeZoneField(default='GMT'),
        ),
    ]
