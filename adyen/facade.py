# -*- coding: utf-8 -*-

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
        success, incoming = response.process()

        order_number = incoming.get(Constants.ORDERID, '')
        reference = incoming.get(Constants.TRANSACTIONID, '')
        method = incoming.get(Constants.OPERATIONTYPE, '')
        amount = int(incoming.get(Constants.AMOUNT))
        status = Constants.STATUS_ACCEPTED if success else Constants.STATUS_DECLINED
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
            raise UnableToTakePayment(incoming.get(Constants.MESSAGE))

        # normalize output data
        output_data = {
            'method': 'adyen',
            'amount': amount,
            'reference': reference,
            'ip_address': ip_address,
        }
        return success, output_data
