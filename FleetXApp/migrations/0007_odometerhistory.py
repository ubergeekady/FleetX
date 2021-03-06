# Generated by Django 2.0.3 on 2018-04-10 02:16

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('FleetXApp', '0006_auto_20180410_0054'),
    ]

    operations = [
        migrations.CreateModel(
            name='OdometerHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(default=datetime.datetime.now)),
                ('reading', models.IntegerField()),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='FleetXApp.Account')),
                ('reported_by', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='FleetXApp.Contact')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='FleetXApp.Vehicle')),
            ],
        ),
    ]
