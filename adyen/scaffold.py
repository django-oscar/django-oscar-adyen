from django.utils import timezone
from oscar.core.loading import get_class

from .config import get_config

Constants = get_class('adyen.gateway', 'Constants')
Facade = get_class('adyen.facade', 'Facade')
MissingFieldException = get_class('adyen.gateway', 'MissingFieldException')


class Scaffold:

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

    # This is the mapping between Adyen-specific and these standard statuses
    ADYEN_TO_COMMON_PAYMENT_STATUSES = {
        Constants.PAYMENT_RESULT_AUTHORISED: PAYMENT_STATUS_ACCEPTED,
        Constants.PAYMENT_RESULT_CANCELLED: PAYMENT_STATUS_CANCELLED,
        Constants.PAYMENT_RESULT_REFUSED: PAYMENT_STATUS_REFUSED,
        Constants.PAYMENT_RESULT_ERROR: PAYMENT_STATUS_ERROR,
        Constants.PAYMENT_RESULT_PENDING: PAYMENT_STATUS_PENDING,
    }

    def __init__(self):
        self.config = get_config()

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

        custom_data = self.get_field_merchant_return_data(request, order_data)
        if custom_data is not None:
            field_specs[Constants.MERCHANT_RETURN_DATA] = custom_data

        return_url = self.get_field_return_url(request, order_data)
        if return_url is not None:
            field_specs[Constants.MERCHANT_RETURN_URL] = return_url

        return field_specs

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

    def _normalize_feedback(self, feedback):
        """
        Convert the facade feedback to a standardized one,
        common to all payment provider backends.
        """
        success, adyen_status, details = feedback
        common_status = self.ADYEN_TO_COMMON_PAYMENT_STATUSES[adyen_status]
        return success, common_status, details

    def handle_payment_feedback(self, request):
        return self._normalize_feedback(Facade().handle_payment_feedback(request))

    def assess_notification_relevance(self, request):
        return Facade().assess_notification_relevance(request)

    def build_notification_response(self, request):
        return Facade().build_notification_response(request)
