# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from .facade import Facade
from .gateway import Constants


class Scaffold():

    def __init__(self, order_data=None):
        self.facade = Facade()
        try:
            for name, value in order_data.items():
                setattr(self, name, value)
        except AttributeError:
            pass

    def get_form_action(self):
        """ Return the URL where the payment form should be submitted. """
        try:
            return settings.ADYEN_ACTION_URL
        except AttributeError:
            raise ImproperlyConfigured("Please set ADYEN_ACTION_URL")

    def get_form_fields(self):
        """ Return the payment form fields, rendered into HTML. """

        fields_list = self.get_form_fields_list()
        return ''.join([
            '<input type="%s" name="%s" value="%s">\n' % (
                f.get('type'), f.get('name'), f.get('value')
            ) for f in fields_list
        ])

    def get_form_fields_list(self):
        """
        Return the payment form fields as a list of dicts.
        """

        now = timezone.now()
        session_validity = now + timezone.timedelta(days=1)
        session_validity_format = '%Y-%m-%dT%H:%M:%SZ'
        ship_before_date = now + timezone.timedelta(days=30)
        ship_before_date_format = '%Y-%m-%d'

        return self.facade.build_payment_form_fields({
            Constants.MERCHANT_ACCOUNT: settings.ADYEN_IDENTIFIER,
            Constants.MERCHANT_REFERENCE: self.order_id,
            Constants.SHOPPER_REFERENCE: self.client_id,
            Constants.SHOPPER_EMAIL: self.client_email,
            Constants.SHOPPER_LOCALE: self.locale,
            Constants.COUNTRY_CODE: self.country_code,
            Constants.CURRENCY_CODE: self.currency_code,
            Constants.PAYMENT_AMOUNT: self.amount,
            Constants.SKIN_CODE: settings.ADYEN_SKIN_CODE,
            Constants.SESSION_VALIDITY: session_validity.strftime(session_validity_format),
            Constants.SHIP_BEFORE_DATE: ship_before_date.strftime(ship_before_date_format),
        })

    def handle_payment_feedback(self, request):
        """
        Handle the post-payment process.
        """
        return self.facade.handle_payment_feedback(request)
