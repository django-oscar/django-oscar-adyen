# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .facade import Facade
from .gateway import Constants


class Scaffold():

    def __init__(self, order_data=None):
        pass

        # self.facade = Facade()
        # try:
        #     for name, value in order_data.items():
        #         setattr(self, name, value)
        # except AttributeError:
        #     pass

    def get_form_action(self):
        """ Return the URL where the payment form should be submitted. """
        pass

        # try:
        #     return settings.BE2BILL_PRIMARY_URL
        # except AttributeError:
        #     raise ImproperlyConfigured("Please set BE2BILL_PRIMARY_URL")

    def get_form_fields(self):
        """ Return the payment form fields, rendered into HTML. """
        pass

        # fields_list = self.get_form_fields_list()
        # return ''.join([
        #     '<input type="%s" name="%s" value="%s">\n' % (
        #         f.get('type'), f.get('name'), f.get('value')
        #     ) for f in fields_list
        # ])

    def get_form_fields_list(self):
        """ Return the payment form fields as a list of dicts. """
        pass

        # return self.facade.build_payment_form_fields({
        #     Constants.CLIENTIDENT: self.client_id,
        #     Constants.ORDERID: self.order_id,
        #     Constants.AMOUNT: self.amount,
        #     Constants.DESCRIPTION: self.description,
        # })

    def handle_payment_feedback(self, request):
        """ Handle the post-payment process. """
        pass

        # return self.facade.handle_payment_feedback(request)
