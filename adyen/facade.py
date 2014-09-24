# -*- coding: utf-8 -*-

import json

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from oscar.apps.payment.exceptions import PaymentError, UnableToTakePayment

from .gateway import Gateway, Constants, PaymentResponse
from .models import AdyenTransaction


class Facade():

    FEEDBACK_MESSAGES = {
        Constants.PAYMENT_RESULT_AUTHORISED: _("Your payment was successful."),
        Constants.PAYMENT_RESULT_REFUSED: _("Your payment was refused."),
        Constants.PAYMENT_RESULT_CANCELLED: _("Your payment was cancelled."),
        Constants.PAYMENT_RESULT_PENDING: _("Your payment is still pending."),
        Constants.PAYMENT_RESULT_ERROR: _(
            "There was a problem with your payment. "
            "We apologize for the inconvenience."
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
        """
        Return a dict containing the name and value of all the hidden fields
        necessary to build the form that will be POSTed to Adyen.
        """
        return self.gateway.build_payment_form_fields(params)

    @classmethod
    def _get_origin_ip_address(cls, request):
        """
        Return the IP address where the payment originated from or None if
        we are unable to get it.

        We need to fetch the *real* origin IP address. According to
        the platform architecture, it may be transmitted to our application
        via vastly variable HTTP headers. The name of the relevant header is
        therefore configurable via the `ADYEN_IP_ADDRESS_HTTP_HEADER` Django
        setting. We fallback on the canonical `REMOTE_ADDR`, used for regular,
        unproxied requests.
        """
        try:
            ip_address_http_header = settings.ADYEN_IP_ADDRESS_HTTP_HEADER
        except AttributeError:
            ip_address_http_header = 'REMOTE_ADDR'

        try:
            ip_address = request.META[ip_address_http_header]
        except KeyError:
            ip_address = None

        return ip_address if ip_address else None

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
        success, status, details = response.process()

        order_number = details.get(Constants.MERCHANT_REFERENCE, '')
        reference = details.get(Constants.PSP_REFERENCE, '')
        method = details.get(Constants.PAYMENT_METHOD, '')

        # Adyen does not provide the payment amount in the
        # return URL, so we store it in this field to
        # avoid a database query to get it back then.
        amount = int(details.get(Constants.MERCHANT_RETURN_DATA))

        ip_address = self._get_origin_ip_address(request)  # None if not found

        # ... and record the audit trail.
        AdyenTransaction.objects.create(
            order_number=order_number,
            reference=reference,
            method=method,
            amount=amount,
            status=status,
            ip_address=ip_address,
        )
        if not success:
            feedback_message = self.FEEDBACK_MESSAGES.get(status)

            # If the customer cancelled their payment, we must raise
            # a specific Exception to allow a different code path in the
            # application above. This specific Exception, however, is not
            # yet available in the official version of Oscar. If we can't
            # find it, we fall back to the default behaviour, which is to
            # lump cancellations with the other failure reasons.
            if status == Constants.PAYMENT_RESULT_CANCELLED:
                try:
                    from oscar.apps.payment.exceptions import PaymentCancelled
                    raise PaymentCancelled(feedback_message)
                except ImportError:
                    pass

            # Otherwise...
            raise UnableToTakePayment(feedback_message)

        # We now normalize the output data to feed it back to the Oscar shop.
        output_data = {
            'method': 'adyen',
            'amount': amount,
            'status': status,
            'details': details,
            'reference': reference,
            'ip_address': ip_address,
        }
        return success, output_data
