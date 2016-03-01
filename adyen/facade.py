# -*- coding: utf-8 -*-

import logging

import iptools
from django.http import HttpResponse
from oscar.core.loading import get_class

from .config import get_config
from .models import AdyenTransaction

Constants = get_class('adyen.gateway', 'Constants')
Gateway = get_class('adyen.gateway', 'Gateway')
PaymentNotification = get_class('adyen.gateway', 'PaymentNotification')
PaymentRedirection = get_class('adyen.gateway', 'PaymentRedirection')


logger = logging.getLogger('adyen')


def get_gateway(request, config):
    """Instantiate a :class:`adyen.gateway.Gateway` from ``config``.

    :param request: Django HTTP request object.
    :param config: Adyen Config object.
    :type config: :class:`~adyen.config.AbstractAdyenConfig`
    :return: An instance of ``Gateway`` configured properly.

    The ``Gateway`` is built using the given ``config`` and ``request`` to get
    specific values for ``identifier``, ``secret_key`` and ``action_url``.

    The configuration object requires the ``request`` in order to allow plugin
    user to define a per-request configuration, such as a different secret key
    based on the country or the language (or even the type of customer, its
    IP address, or other request specific parameter).
    """
    return Gateway({
        Constants.IDENTIFIER: config.get_identifier(request),
        Constants.SECRET_KEY: config.get_skin_secret(request),
        Constants.ACTION_URL: config.get_action_url(request),
    })


class Facade:
    """Facade used to expose the public behavior of the Adyen gateway.

    The ``Facade`` class exposes a set of public methods to be used by the
    plugin internally and by plugin users without having to deal with Adyen
    internal mecanism (such as how to sign a request form or how to read a
    payment response).

    The first entry point is the payment form:

    * :meth:`build_payment_form_fields` to handle payment data and generate
      the payment request form used to submit a payment request to Adyen HPP.

    Then payment processing entry points of the ``Facade`` are:

    * :meth:`handle_payment_return` to handle payment return data,
    * :meth:`handle_payment_notification` to handle payment standard
      notifications.

    These methods will build an appropriate Adyen Payment Response object and
    call the :meth:`process_payment_feedback` method to handle the payment
    feedback.
    """
    def __init__(self):
        self.config = get_config()

    def build_payment_form_fields(self, request, params):
        """
        Return a dict containing the name and value of all the hidden fields
        necessary to build the form that will be POSTed to Adyen.
        """
        return get_gateway(request, self.config).build_payment_form_fields(params)

    @classmethod
    def _is_valid_ip_address(cls, s):
        """
        Make sure that a string is a valid representation of an IP address.
        Relies on the iptools package, even though Python 3.4 gave us the new
        shiny `ipaddress` module in the stdlib.
        """
        return iptools.ipv4.validate_ip(s) or iptools.ipv6.validate_ip(s)

    def _get_origin_ip_address(self, request):
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
        ip_address_http_header = self.config.get_ip_address_header()

        try:
            ip_address = request.META[ip_address_http_header]
        except KeyError:
            return None

        if not self._is_valid_ip_address(ip_address):
            logger.warn("%s is not a valid IP address", ip_address)
            return None

        return ip_address

    def build_payment_return(self, request):
        """Build a Payment Return response object from raw request.

        :param request: Django HTTP request object
        :return: A :class:`~adyen.gateway.PaymentRedirection` object

        This method get the gateway for the ``request`` and :attr:`config`
        and instantiate a :class:`~adyen.gateway.PaymentRedirection` with this
        gateway and the ``request.GET`` parameters.

        Plugin users may want to override this method to build any user-made
        object to handle their own specific cases.
        """
        gateway = get_gateway(request, self.config)
        return PaymentRedirection(gateway, request.GET)

    def build_payment_notification(self, request):
        """Build a Payment Notification response object from raw request.

        :param request: Django HTTP request object
        :return: A :class:`~adyen.gateway.PaymentNotification` object

        This method get the gateway for the ``request`` and :attr:`config`
        and instantiate a :class:`~adyen.gateway.PaymentNotification` with this
        gateway and the ``request.POST`` parameters.

        Plugin users may want to override this method to build any user-made
        object to handle their own specific cases.
        """
        gateway = get_gateway(request, self.config)
        return PaymentNotification(gateway, request.POST)

    def unpack_details(self, details):
        """Unpack detailed information from ``response.process()``

        :param dict details: Dict that contains data from an Adyen
            notification or when customer come back through the return URL.
        :return: A dict with transaction details.

        .. seealso::

            :meth:`unpack_details_amount` can be overridden to extract the
            transaction amount. Note that this plugin decided to use a field
            for this purpose.

            :meth:`unpack_merchant_return_data` can be overridden to extract
            specific data from ``merchantReturnData``. This method is called
            *after* any others and can be used to override the initial unpacked
            details.

        """
        order_number = details.get(Constants.MERCHANT_REFERENCE, '')
        payment_method = details.get(Constants.PAYMENT_METHOD, '')
        psp_reference = details.get(Constants.PSP_REFERENCE, '')

        unpacked_details = {
            'order_number': order_number,
            'payment_method': payment_method,
            'psp_reference': psp_reference,
            'amount': self.unpack_details_amount(details),
        }

        # Update details with merchant return data.
        unpacked_details.update(
            self.unpack_merchant_return_data(details))

        return unpacked_details

    def unpack_details_amount(self, details):
        """Unpack amount from the Adyen response details.

        :param dict details: Dict that contains data from an Adyen
            notification or when customer come back through the return URL.
        :return: None if amount is not available or an integer.

        The payment amount is transmitted by the notification in the ``value``
        field. However, in the case of a payment return URL, we do not have
        this parameter.

        We decided in ``Scaffold.get_field_merchant_return_data`` to provide
        the order's amount into this field, but this is not standard. As
        developers may want to override this behavior, they can extend both
        part in order to modify only the behavior of the field
        ``merchantReturnData``, and they can override this method to fetch
        amount in their own way.
        """
        value = details.get(Constants.VALUE)

        # The payment amount is transmitted in a different parameter whether
        # we are in the context of a PaymentRedirection (`merchantReturnData`)
        # or a PaymentNotification (`value`). Both fields are mandatory in the
        # respective context, ensuring we always get back our amount.
        # This is, however, not generic in case of using the backend outside
        # the Oscaro Shop project, since it is our decision to store the amount
        # in the `merchantReturnData` field.
        # This is kept for backward compatible reason.
        amount = details.get(Constants.MERCHANT_RETURN_DATA, value)

        if amount is not None:
            return int(amount)

        return None

    def unpack_merchant_return_data(self, details):
        """Unpack merchant return data fields from the ``details``.

        :param dict details: Dict that contains data from an Adyen
            notification or when customer come back through the return URL.
        :return: A dict of extra details to unpack that handle custom fields.

        The return dict is supposed to contain the ``merchant_return_data``,
        which is by default the raw content of the field
        ``merchantReturnData``.

        Developers may want to override the meaning of this field and extract
        various other information.

        .. note::

            The result of this method will override any existing key extracted
            in :meth:`unpack_details`. It is powerful yet it could be dangerous
            if not handled with care.

        """
        merchant_return_data = details.get(
            Constants.MERCHANT_RETURN_DATA, None)
        return {
            'merchant_return_data': merchant_return_data
        }

    def _record_audit_trail(self, request, status, txn_details):
        """
        Record an AdyenTransaction to keep track of the current payment attempt.
        """
        reference = txn_details['psp_reference']

        # We record the audit trail.
        try:
            txn_log = AdyenTransaction.objects.create(
                amount=txn_details['amount'],
                method=txn_details['payment_method'],
                order_number=txn_details['order_number'],
                reference=reference,
                status=status,
            )
        except Exception:  # pylint: disable=W0703

            # Yes, this is generic, because basically, whatever happens, be it
            # a `KeyError` in `txn_details` or an exception when creating our
            # `AdyenTransaction`, we are going to do the same thing: log the
            # exception and carry on. This is not critical, and this should
            # not prevent the rest of the process.
            logger.exception("Unable to record audit trail for transaction "
                             "with reference %s", reference)
            return

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

    def handle_payment_return(self, request):
        """Handle payment return.

        :param request: Django HTTP request (GET)

        This method should be called when customers come back from the Adyen
        HPP (through a ``GET`` request). It instantiate the gateway and the
        appropriate response object and pass it to
        :meth:`process_payment_feedback` to return a result.
        """
        response = self.build_payment_return(request)
        return self.process_payment_feedback(request, response)

    def handle_payment_notification(self, request):
        """Handle payment notification.

        :param request: Django HTTP request (POST)

        This method should be called when Adyen send its Payment Notification
        (through a ``POST`` request). It instantiate the gateway and the
        appropriate response object and pass it to
        :meth:`process_payment_feedback` to return a result.
        """
        response = self.build_payment_notification(request)
        return self.process_payment_feedback(request, response)

    def handle_payment_feedback(self, request):
        """Handle payment feedback (payment return or payment notification).

        .. deprecated:: 0.6.0

            This method is not used internally anymore by the plugin. If you
            rely on that please switch to :meth:`handle_payment_return`,
            :meth:`handle_payment_notification`, and
            :meth:`process_payment_feedback`.

        """
        if request.method == 'GET':
            return self.handle_payment_return(request)
        elif request.method == 'POST':
            return self.handle_payment_notification(request)
        else:
            raise RuntimeError("Only GET and POST requests are supported.")

    def process_payment_feedback(self, request, response):
        """Process payment feedback response.

        :param request: Django HTTP request object
        :param response: Adyen payment response

        Validate, process, optionally record audit trail and provide feedback
        about the current payment response.
        """
        # Note that this may raise an exception if the response is invalid.
        # For example: MissingFieldException, UnexpectedFieldException, ...
        # The code "above" should be prepared to deal with it accordingly.
        response.validate()

        # Then, we can extract the received data...
        success, status, details = response.process()
        txn_details = self.unpack_details(details)

        # ... and record the audit trail.
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

    def assess_notification_relevance(self, request):
        """
        Return a (must_process, must_acknowledge) tuple to decide what should
        be done with this request.
        """

        # Only POST requests should be considered.
        if request.method != 'POST':
            return False, False

        # Requests may originate from the Adyen `live` or `test` platform.
        # We should completely ignore those whose origin does not match
        # the current execution platform. To do so:
        # - On one hand we have the `ADYEN_ACTION_URL` setting, from which
        # we can extract the platform we are currently running against.
        # - On the other hand we have the `live` POST parameter, which lets
        # us know which Adyen platform fired this request.
        current_platform = (Constants.LIVE
                            if Constants.LIVE in self.config.get_action_url(request)
                            else Constants.TEST)

        origin_platform = (Constants.LIVE
                           if request.POST.get(Constants.LIVE) == Constants.TRUE
                           else Constants.TEST)

        if current_platform != origin_platform:
            return False, False

        # Adyen fires notifications for many kinds of events, but as far as
        # we are concerned here, we only care about payment authorizations.
        # However, we should probably acknowledge all those notifications so
        # Adyen doesn't keep sending them forever and ever.
        if request.POST.get(Constants.EVENT_CODE) != Constants.EVENT_CODE_AUTHORISATION:
            return False, True

        reference = request.POST[Constants.PSP_REFERENCE]

        # Adyen has a notification check that can be run from their control panel.
        # It's useful to debug connection problems between Adyen and our servers.
        # So we acknowledge them, but must not process them.
        if Constants.TEST_REFERENCE_PREFIX in reference:
            return False, True

        # Adyen duplicates many notifications. This bit makes sure we ignore them.
        # "Duplicate notifications have the same corresponding values for their eventCode and
        # pspReference fields."  https://docs.adyen.com/display/TD/Accept+notifications
        # The event code gets checked above, so we only need to check for the reference now.
        if AdyenTransaction.objects.filter(reference=reference).exists():
            # We already stored a transaction with this reference, so we can ignore the
            # notification. As above, we still acknowledge it to Adyen, in case it missed
            # our previous acknowledgment.
            return False, True

        # Seems legit, just do it :)
        return True, True

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
