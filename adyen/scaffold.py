from django.utils import timezone
from oscar.core.loading import get_class

from .config import get_config

Constants = get_class('adyen.gateway', 'Constants')
Facade = get_class('adyen.facade', 'Facade')
MissingFieldException = get_class('adyen.gateway', 'MissingFieldException')


class Scaffold:
    """Entry point to handle Adyen HPP.

    The ``Scaffold`` exposes an interface that can be used in any Django Oscar
    application. It aims to hide the inner complexity of payment form
    management and payment notification processing.

    The key methods are:

    * :meth:`get_form_action` and `get_form_fields` to build the Adyen HPP
      request submission form,
    * :meth:`handle_payment_return` to handle customer coming back from the
      Adyen HPP after a payment (successful or not)
    * :meth:`assess_notification_relevance`,
      :meth:`handle_payment_notification` and
      :meth:`build_notification_response` to handle Adyen Payment Notification.

    """
    # These are the constants that all scaffolds are expected to return
    # to a multi-psp application. They might look like those actually returned
    # by the psp itself, but that would be a pure coincidence.
    # At some point we could discuss merging cancelled & refused & error and just
    # ensuring good error messages are returned. I doubt the distinction is
    # important to most checkout procedures.
    PAYMENT_STATUS_ACCEPTED = 'ACCEPTED'
    PAYMENT_STATUS_CANCELLED = 'CANCELLED'
    PAYMENT_STATUS_REFUSED = 'REFUSED'
    PAYMENT_STATUS_ERROR = 'ERROR'
    PAYMENT_STATUS_PENDING = 'PENDING'

    #: This is the mapping between Adyen-specific and these standard statuses
    ADYEN_TO_COMMON_PAYMENT_STATUSES = {
        Constants.PAYMENT_RESULT_AUTHORISED: PAYMENT_STATUS_ACCEPTED,
        Constants.PAYMENT_RESULT_CANCELLED: PAYMENT_STATUS_CANCELLED,
        Constants.PAYMENT_RESULT_REFUSED: PAYMENT_STATUS_REFUSED,
        Constants.PAYMENT_RESULT_ERROR: PAYMENT_STATUS_ERROR,
        Constants.PAYMENT_RESULT_PENDING: PAYMENT_STATUS_PENDING,
    }

    def __init__(self):
        self.config = get_config()

    def _normalize_feedback(self, feedback):
        """
        Convert the facade feedback to a standardized one,
        common to all payment provider backends.
        """
        success, adyen_status, details = feedback
        common_status = self.ADYEN_TO_COMMON_PAYMENT_STATUSES[adyen_status]
        return success, common_status, details

    def get_form_action(self, request):
        """ Return the URL where the payment form should be submitted. """
        return self.config.get_action_url(request)

    def get_form_fields(self, request, order_data):
        """
        Return the payment form fields as a list of dicts.
        Expects a large-ish order_data dictionary with details of the order.
        """
        field_specs = self.get_field_specs(request, order_data)
        return Facade().build_payment_form_fields(request, field_specs)

    def get_field_specs(self, request, order_data):
        now = timezone.now()
        session_validity = now + timezone.timedelta(minutes=20)
        session_validity_format = '%Y-%m-%dT%H:%M:%SZ'
        ship_before_date = now + timezone.timedelta(days=30)
        ship_before_date_format = '%Y-%m-%d'

        # Build common field specs
        try:
            field_specs = {
                Constants.MERCHANT_ACCOUNT: self.config.get_identifier(request),
                Constants.SKIN_CODE: self.config.get_skin_code(request),
                Constants.SESSION_VALIDITY: session_validity.strftime(session_validity_format),
                Constants.SHIP_BEFORE_DATE: ship_before_date.strftime(ship_before_date_format),

                Constants.MERCHANT_REFERENCE: str(order_data['order_number']),
                Constants.SHOPPER_REFERENCE: order_data['client_id'],
                Constants.SHOPPER_EMAIL: order_data['client_email'],
                Constants.CURRENCY_CODE: order_data['currency_code'],
                Constants.PAYMENT_AMOUNT: order_data['amount'],
                Constants.SHOPPER_LOCALE: order_data['shopper_locale'],
                Constants.COUNTRY_CODE: order_data['country_code'],
            }
        except KeyError:
            raise MissingFieldException(
                "One or more fields are missing from the order data.")

        allowed_methods = self.get_field_allowed_methods(request, order_data)
        if allowed_methods is not None:
            field_specs[Constants.ALLOWED_METHODS] = allowed_methods

        custom_data = self.get_field_merchant_return_data(request, order_data)
        if custom_data is not None:
            field_specs[Constants.MERCHANT_RETURN_DATA] = custom_data

        return_url = self.get_field_return_url(request, order_data)
        if return_url is not None:
            field_specs[Constants.MERCHANT_RETURN_URL] = return_url

        return field_specs

    def get_field_allowed_methods(self, request, order_data):
        """Get a string of comma separated allowed payment methods.

        :param request: Django HTTP request object.
        :param dict order_data: Order's data.
        :return: If defined by the configuration, a string composed of a list
            of comma separated payment methods (ex. ``card,bankTransfert``).
            Otherwise ``None``.

        This methods is used to populate the ``allowedMethods`` field of the
        payment request form. See `Adyen HPP manual`__ for more information.

        .. __: https://docs.adyen.com/manuals/hpp-manual/hosted-payment-pages/hpp-payment-methods

        If a ``source_type`` is available into the provided ``order_data``,
        then it is used as a parameter to
        :meth:`adyen.config.AbstractAdyenConfig.get_allowed_methods`.

        .. versionadded:: 0.6.0

            Added to handle ``allowedMethods`` field. May require extra work
            on the configuration object to work properly.

        """
        source_type = order_data.get('source_type', None)

        try:
            allowed_methods = self.config.get_allowed_methods(request,
                                                              source_type)
        except NotImplementedError:
            # New in version 0.6.0: this may not work properly with existing
            # application using this plugin. We make sure not to break here
            # and keep this plugin backward-compatible with version 0.5.
            return None

        if not allowed_methods:
            return None

        return ','.join(method.strip() for method in allowed_methods)

    def get_field_merchant_return_data(self, request, order_data):
        # Adyen does not provide the payment amount in the return URL, so we
        # store it in this field to avoid a database query to get it back then.
        return order_data['amount']

    def get_field_return_url(self, request, order_data):
        # Check for overridden return URL.
        return_url = order_data.get('return_url', None)

        if not return_url:
            return None

        return return_url.replace('PAYMENT_PROVIDER_CODE', Constants.ADYEN)

    def handle_payment_feedback(self, request):
        """Handle payment feedback from return URL or POST notification.

        :param request: Django HTTP request object.
        :return: A normalized payment feedback.

        If the ``request.method`` is ``POST``, this method consider we handle
        an Adyen Payment Notification. Otherwise it considers it is a simple
        Payment Return case.

        .. seealso::

            :meth:`handle_payment_notification` and
            :meth:`handle_payment_return` to see how to handle both cases.

        .. deprecated:: 0.6.0

            This method is deprecated in favor of more specific methods and
            should not be used in plugin user's code anymore.

        """
        if request.method == 'POST':
            return self.handle_payment_notification(request)

        return self.handle_payment_return(request)

    def handle_payment_return(self, request):
        """Handle payment return.

        :param request: Django HTTP request object
        :return: A 3-values tuple with ``success``, ``status`` and ``details``.

        One should call this method when handling the GET request that come
        after a redirection from Adyen.

        .. versionadded:: 0.6.0

            This method has been added to replace the generic
            :meth:`handle_payment_feedback`.

        """
        facade = Facade()
        result = facade.handle_payment_return(request)
        return self._normalize_feedback(result)

    def handle_payment_notification(self, request):
        """Handle payment notification.

        :param request: Django HTTP request object
        :return: A 3-values tuple with ``success``, ``status`` and ``details``.

        One should call this method when handling the POST request that come
        as an Adyen Payment Notification.

        .. versionadded:: 0.6.0

            This method has been added to replace the generic
            :meth:`handle_payment_feedback`.

        """
        facade = Facade()
        result = facade.handle_payment_notification(request)
        return self._normalize_feedback(result)

    def assess_notification_relevance(self, request):
        """Assess if a notification request is relevant.

        :param request: Django HTTP request object.
        :return: A 2-value tuple as ``must_process`` and ``must_acknowledge``

        One should call this method when receiving a notification request and
        they want to know if the notification must:

        1. Be processed, ie. is a call to :meth:`handle_payment` is relevant,
        2. Be acknowledged with a response to Adyen, using
           :meth:`build_notification_response`

        .. versionadded:: 0.6.0

            This method has been added to replace the generic
            :meth:`handle_payment_feedback`.

        """
        return Facade().assess_notification_relevance(request)

    def build_notification_response(self, request):
        """Build a notification response for an Adyen Payment Notification

        :param request: Django HTTP request object.
        :return: A Django HTTP Response object.

        From the ``Adyen Integration Manual``:

            The Adyen notification system requires a response within 30 seconds
            of receipt of the notification, the server is expecting a response
            of ``[accepted]``, including the brackets. When our systems receive
            this response all notifications contained in the message are marked
            as successfully sent."

        This method simply call the
        :meth:`adyen.facade.Facade.build_notification_response` method and
        returns its result.
        """
        return Facade().build_notification_response(request)
