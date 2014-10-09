# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AdyenTransaction',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('order_number', models.CharField(db_index=True, max_length=255, unique=True)),
                ('reference', models.CharField(max_length=255)),
                ('method', models.CharField(max_length=255, blank=True)),
                ('status', models.CharField(max_length=255, blank=True)),
                ('amount', models.DecimalField(max_digits=12, blank=True, decimal_places=2, null=True)),
                ('currency', models.CharField(max_length=3, default='EUR')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'ordering': ('-date_created',),
            },
            bases=(models.Model,),
        ),
    ]
