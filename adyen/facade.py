# -*- coding: utf-8 -*-

import json

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from oscar.core.loading import get_class
PaymentError = get_class('payment.exceptions', 'PaymentError')
UnableToTakePayment = get_class('payment.exceptions', 'UnableToTakePayment')

from .gateway import Gateway, Constants, PaymentResponse
from .models import AdyenTransaction


class Facade():

    FEEDBACK_MESSAGES = {
        Constants.PAYMENT_RESULT_AUTHORISED: _("Your payment was successful."),
        Constants.PAYMENT_RESULT_REFUSED: _("Your payment was refused."),
        Constants.PAYMENT_RESULT_CANCELLED: _("Your payment was cancelled."),
        Constants.PAYMENT_RESULT_PENDING: _("Your payment is still pending."),
        Constants.PAYMENT_RESULT_ERROR: _(
            "There was a problem with your payment. We apologize for the inconvenience"
        ),
    }

    def __init__(self, **kwargs):
        init_params = {
            Constants.IDENTIFIER: settings.ADYEN_IDENTIFIER,
            Constants.SECRET_KEY: settings.ADYEN_SECRET_KEY,
            Constants.ACTION_URL: settings.ADYEN_ACTION_URL,
        }
        # Initialize the gateway.
        self.gateway = Gateway(init_params)

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
        response = PaymentResponse(client, query_string)

        # Note that this may raise an exception if the response is invalid.
        # For example: MissingFieldException, UnexpectedFieldException, ...
        # The code "above" should be prepared to deal with it accordingly.
        response.validate()

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

        # FIXME: This is a naive way of getting the origin IP address
        # Behind a proxy, this would actually contain the proxy's IP
        # which we definitely don't care about.
        # The canonical implementation in that case seems to be to use
        # a HTTP_X_FORWARDED_FOR header (see:
        # http://www.micahcarrick.com/django-ip-address-behind-nginx-proxy.html)
        # but I'm not quite sure yet it is THE way.
        # This is worth discussing, but not worth blocking the merge.

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
            feedback_code = details.get(Constants.AUTH_RESULT, Constants.PAYMENT_RESULT_ERROR)
            feedback_message = self.FEEDBACK_MESSAGES.get(feedback_code)
            raise UnableToTakePayment(feedback_message)

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
