# -*- coding: utf-8 -*-

import bleach

from django.utils import timezone

from .facade import Facade
from .gateway import Constants, MissingFieldException
from .config import get_config


class Scaffold:

    # These are the constants that all scaffolds are expected to return
    # to a multi-psp application. They might look like those actually returned
    # by the psp itself, but that would be a pure coincidence.
    PAYMENT_STATUS_ACCEPTED = 'ACCEPTED'
    PAYMENT_STATUS_CANCELLED = 'CANCELLED'
    PAYMENT_STATUS_REFUSED = 'REFUSED'

    # This is the mapping between Adyen-specific and these standard statuses
    ADYEN_TO_COMMON_PAYMENT_STATUSES = {
        Constants.PAYMENT_RESULT_AUTHORISED: PAYMENT_STATUS_ACCEPTED,
        Constants.PAYMENT_RESULT_CANCELLED: PAYMENT_STATUS_CANCELLED,
        Constants.PAYMENT_RESULT_REFUSED: PAYMENT_STATUS_REFUSED,
    }

    def __init__(self, order_data=None):
        # This is an anti-pattern. We require passing in additional data
        # when the Scaffold is initialized (instead of when calling the methods that
        # might require that data). get_form_fields_list especially relies on this.
        # This makes the code very Oscaro-specific.
        try:
            for name, value in order_data.items():
                setattr(self, name, value)
        except AttributeError:
            pass

    def get_form_action(self, request):
        """ Return the URL where the payment form should be submitted. """
        return get_config().get_action_url(request)

    def get_form_fields(self, request):
        """ Return the payment form fields, rendered into HTML. """

        fields_list = self.get_form_fields_list(request)
        return ''.join([
            '<input type="%s" name="%s" value="%s">\n' % (
                f.get('type'), f.get('name'), bleach.clean(f.get('value'))
            ) for f in fields_list
        ])

    def get_form_fields_list(self, request):
        """
        Return the payment form fields as a list of dicts.
        """
        now = timezone.now()
        session_validity = now + timezone.timedelta(minutes=20)
        session_validity_format = '%Y-%m-%dT%H:%M:%SZ'
        ship_before_date = now + timezone.timedelta(days=30)
        ship_before_date_format = '%Y-%m-%d'

        # Build common field specs
        try:
            field_specs = {
                Constants.MERCHANT_ACCOUNT: get_config().get_identifier(request),
                Constants.SKIN_CODE: get_config().get_skin_code(request),
                Constants.SESSION_VALIDITY: session_validity.strftime(session_validity_format),
                Constants.SHIP_BEFORE_DATE: ship_before_date.strftime(ship_before_date_format),

                # The following values must be passed in via order_data in __init__().
                Constants.MERCHANT_REFERENCE: str(self.order_number),
                Constants.SHOPPER_REFERENCE: self.client_id,
                Constants.SHOPPER_EMAIL: self.client_email,
                Constants.CURRENCY_CODE: self.currency_code,
                Constants.PAYMENT_AMOUNT: self.amount,
                Constants.SHOPPER_LOCALE: self.shopper_locale,
                Constants.COUNTRY_CODE: self.country_code,
                # Adyen does not provide the payment amount in the return URL, so we store it in
                # this field to avoid a database query to get it back then.
                Constants.MERCHANT_RETURN_DATA: self.amount,

            }

        except AttributeError:
            raise MissingFieldException

        # Check for overridden return URL.
        return_url = getattr(self, 'return_url', None)
        if return_url is not None:
            return_url = return_url.replace('PAYMENT_PROVIDER_CODE', Constants.ADYEN)
            field_specs[Constants.MERCHANT_RETURN_URL] = return_url

        return Facade().build_payment_form_fields(request, field_specs)

    def _normalize_feedback(self, feedback):
        """
        Convert the facade feedback to a standardized one,
        common to all payment provider backends.
        """
        success, adyen_status, details = feedback
        common_status = self.ADYEN_TO_COMMON_PAYMENT_STATUSES.get(adyen_status)
        return success, common_status, details

    def handle_payment_feedback(self, request):
        return self._normalize_feedback(
            Facade().handle_payment_feedback(request, record_audit_trail=True))

    def check_payment_outcome(self, request):
        return self._normalize_feedback(
            Facade().handle_payment_feedback(request, record_audit_trail=False))

    def assess_notification_relevance(self, request):
        return Facade().assess_notification_relevance(request)

    def build_notification_response(self, request):
        return Facade().build_notification_response(request)
