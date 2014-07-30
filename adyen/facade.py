# -*- coding: utf-8 -*-

import json

from django.conf import settings

from oscar.core.loading import get_class
PaymentError = get_class('payment.exceptions', 'PaymentError')
UnableToTakePayment = get_class('payment.exceptions', 'UnableToTakePayment')

from .gateway import Gateway, Constants, PaymentResponse
from .models import AdyenTransaction


class Facade():

    def __init__(self):
        self.gateway = Gateway({
            'identifier': settings.ADYEN_IDENTIFIER,
            'secret_key': settings.ADYEN_SECRET_KEY,
            'action_url': settings.ADYEN_ACTION_URL,
        })

    def build_payment_form_fields(self, params):
        """ Return a dict containing the name and value
            of all the hidden fields necessary to build
            the form that will be POSTed to the payment
            provider.
        """
        return self.gateway.build_payment_form_fields(params)

    def handle_payment_feedback(self, request):
        success, output_data = False, {}

        # first, let's validate the Adyen response
        client = self.gateway
        query_string = request.META['QUERY_STRING']
        try:
            response = PaymentResponse(client, query_string)
            response.validate()
        except Exception as ex:
            raise

        # then, extract received data
        success, details = response.process()

        order_number = details.get(Constants.MERCHANT_REFERENCE, '')
        reference = details.get(Constants.PSP_REFERENCE, '')
        method = details.get(Constants.PAYMENT_METHOD, '')

        # Adyen does not provide the payment amount in the
        # return URL, so we store it in this field to
        # avoid a database query to get it back then.
        amount = int(details.get(Constants.MERCHANT_RETURN_DATA))

        if success:
            status = Constants.PAYMENT_RESULT_AUTHORISED
        else:
            status = Constants.PAYMENT_RESULT_REFUSED

        ip_address = request.META['REMOTE_ADDR']

        # record audit trail
        AdyenTransaction.objects.create(
            order_number=order_number,
            reference=reference,
            method=method,
            amount=amount,
            status=status,
            ip_address=ip_address,
        )
        if not success:

            # TODO(MR): Provide customer feedback in case of refused payment.

            raise UnableToTakePayment(details.get(Constants.MESSAGE))

        # normalize output data
        output_data = {
            'method': 'adyen',
            'amount': amount,
            'status': status,
            'details': details,
            'reference': reference,
            'ip_address': ip_address,
        }
        return success, output_data
