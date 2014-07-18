# -*- coding: utf-8 -*-

from django.db import models
from django.conf import settings
from django.utils import timezone

from .gateway import Constants


class AdyenTransaction(models.Model):

    # Note we don't use a foreign key as the order hasn't been created
    # by the time the transaction takes place
    order_number = models.CharField(max_length=255, db_index=True)

    reference = models.CharField(max_length=255)
    method = models.CharField(max_length=255, default=Constants.OPERATIONTYPE_PAYMENT)
    status = models.CharField(max_length=255, blank=True)

    amount = models.DecimalField(decimal_places=2, max_digits=12, blank=True, null=True)
    currency = models.CharField(max_length=3, default=settings.ADYEN_CURRENCY)

    ip_address = models.GenericIPAddressField(blank=True, null=True)
    date_created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('-date_created',)

    def __str__(self):
        return u'%s txn for order %s - ref: %s, status: %s' % (
            self.method.upper(),
            self.order_number,
            self.reference,
            self.status)

    def __unicode__(self):
        return str(self)

    @property
    def accepted(self):
        return self.status == Constants.STATUS_ACCEPTED

    @property
    def declined(self):
        return self.status == Constants.STATUS_DECLINED
