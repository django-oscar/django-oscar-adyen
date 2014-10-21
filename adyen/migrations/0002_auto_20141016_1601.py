# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('adyen', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adyentransaction',
            name='order_number',
            field=models.CharField(max_length=255),
        ),
    ]
