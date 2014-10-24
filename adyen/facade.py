# -*- coding: utf-8 -*-

import iptools
import logging

from django.conf import settings
from django.http import HttpResponse

from .gateway import Constants, Gateway, PaymentNotification, PaymentRedirection
from .models import AdyenTransaction

logger = logging.getLogger('adyen')


class Facade():

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
    def _is_valid_ip_address(cls, s):
        """
        Make sure that a string is a valid representation of an IP address.
        Relies on the iptools package, even though Python 3.4 gave us the new
        shiny `ipaddress` module in the stdlib.
        """
        return iptools.ipv4.validate_ip(s) or iptools.ipv6.validate_ip(s)

    @classmethod
    def _get_origin_ip_address(cls, request):
        """
        Return the IP address where the payment originated from or None if
        we are unable to get it -- which *will* happen if we received a
        PaymentNotification rather than a PaymentRedirection, since the
        request, in that case, comes from the Adyen servers.

        When possible, we need to fetch the *real* origin IP address.
        According to the platform architecture, it may be transmitted to our
        application via vastly variable HTTP headers. The name of the relevant
        header is therefore configurable via the `ADYEN_IP_ADDRESS_HTTP_HEADER`
        Django setting. We fallback on the canonical `REMOTE_ADDR`, used for
        regular, unproxied requests.
        """
        try:
            ip_address_http_header = settings.ADYEN_IP_ADDRESS_HTTP_HEADER
        except AttributeError:
            ip_address_http_header = 'REMOTE_ADDR'

        try:
            ip_address = request.META[ip_address_http_header]
        except KeyError:
            return None

        if not cls._is_valid_ip_address(ip_address):
            logger.warn("%s is not a valid IP address" % ip_address)
            return None

        return ip_address

    def _unpack_details(self, details):
        """
        Helper: extract data from the return value of `response.process`.
        """
        merchant_ref = details.get(Constants.MERCHANT_REFERENCE, '')
        customer_id, basket_id, order_number = merchant_ref.split(Constants.SEPARATOR)
        psp_reference = details.get(Constants.PSP_REFERENCE, '')
        payment_method = details.get(Constants.PAYMENT_METHOD, '')

        # The payment amount is transmitted in a different parameter whether
        # we are in the context of a PaymentRedirection (`merchantReturnData`)
        # or a PaymentNotification (`value`). Both fields are mandatory in the
        # respective context, ensuring we always get back our amount.
        # This is, however, not generic in case of using the backend outside
        # the oshop project, since it is our decision to store the amount in
        # the `merchantReturnData` field. Leaving a TODO here to make this more
        # generic at a later date.
        amount = int(details.get(Constants.MERCHANT_RETURN_DATA, details.get(Constants.VALUE)))

        return {
            'amount': amount,
            'basket_id': basket_id,
            'customer_id': customer_id,
            'order_number': order_number,
            'payment_method': payment_method,
            'psp_reference': psp_reference,
        }

    def _record_audit_trail(self, request, status, txn_details):
        """
        Record an AdyenTransaction to keep track of the current payment attempt.
        """
        reference = txn_details['psp_reference']

        # We record the audit trail.
        try:
            txn_log = AdyenTransaction.objects.create(
                order_number=txn_details['order_number'],
                reference=reference,
                method=txn_details['payment_method'],
                amount=txn_details['amount'],
                status=status,
            )
        except Exception as error:
            logger.exception("unexpected error during audit trail recording for transaction "
                             "with reference %s : %s", reference, error)

        # If we received a PaymentNotification via a POST request, we cannot
        # accurately record the origin IP address. It will, however, be made
        # available in the daily Received Payment Report, which we can then
        # process to reconcile the data (TODO at some point).
        if request.method == 'POST':
            return

        # Otherwise, we try to record the origin IP address.
        ip_address = self._get_origin_ip_address(request)  # None if not found
        if ip_address is not None:
            try:
                txn_log.ip_address = ip_address
                txn_log.save()
            except NameError:

                # This means txn_log is not defined, which means the audit
                # trail hasn't been successfully recorded above -- in which
                # case, we have already informed our users.

                pass

    def handle_payment_feedback(self, request, record_audit_trail):
        """
        Validate, process, optionally record audit trail and provide feedback
        about the current payment response.
        """
        success, output_data = False, {}

        # We must first find out whether this is a redirection or a notification.
        client = self.gateway
        params = response_class = None

        if request.method == 'GET':
            params = request.GET
            response_class = PaymentRedirection
        elif request.method == 'POST':
            params = request.POST
            response_class = PaymentNotification
        else:
            raise RuntimeError("Only GET and POST requests are supported.")

        # Then we can instantiate the appropriate class from the gateway.
        response = response_class(client, params)

        # Note that this may raise an exception if the response is invalid.
        # For example: MissingFieldException, UnexpectedFieldException, ...
        # The code "above" should be prepared to deal with it accordingly.
        response.validate()

        # Then, we can extract the received data...
        success, status, details = response.process()
        txn_details = self._unpack_details(details)

        # ... and record the audit trail if instructed to...
        if record_audit_trail:
            self._record_audit_trail(request, status, txn_details)

        # ... prepare the feedback data...
        output_data = {
            'method': Constants.ADYEN,
            'status': status,
            'txn_details': details,
            'ip_address': self._get_origin_ip_address(request),
        }

        # ... also provide the "unpacked" version for easier consumption...
        output_data.update(txn_details)

        # ... and finally return the whole thing.
        return success, status, output_data

    def build_notification_response(self, request):
        """
        Return the appropriate response to send to the Adyen servers to
        acknowledge a transaction notification.

        Quoting the `Adyen Integration Manual` (page 26):

        "The Adyen notification system requires a response within 30 seconds
        of receipt of the notification, the server is expecting a response of
        [accepted], including the brackets. When our systems receive this
        response all notifications contained in the message are marked as
        successfully sent."
        """
        return HttpResponse(Constants.ACCEPTED_NOTIFICATION)
