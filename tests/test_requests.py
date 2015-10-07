from django.conf import settings
from django.test import TestCase, override_settings

from freezegun import freeze_time

from adyen.gateway import MissingFieldException
from adyen.scaffold import Scaffold


TEST_RETURN_URL = 'https://www.example.com/checkout/return/adyen/'

EXPECTED_FIELDS_LIST = [
    {'type': 'hidden', 'name': 'currencyCode', 'value': 'EUR'},
    {'type': 'hidden', 'name': 'merchantAccount', 'value': settings.ADYEN_IDENTIFIER},
    {'type': 'hidden', 'name': 'merchantReference', 'value': '00000000123'},
    {'type': 'hidden', 'name': 'merchantReturnData', 'value': 123},
    {'type': 'hidden', 'name': 'merchantSig', 'value': 'kKvzRvx7wiPLrl8t8+owcmMuJZM='},
    {'type': 'hidden', 'name': 'paymentAmount', 'value': 123},
    {'type': 'hidden', 'name': 'resURL', 'value': TEST_RETURN_URL},
    {'type': 'hidden', 'name': 'sessionValidity', 'value': '2014-07-31T17:20:00Z'},
    {'type': 'hidden', 'name': 'shipBeforeDate', 'value': '2014-08-30'},
    {'type': 'hidden', 'name': 'shopperEmail', 'value': 'test@example.com'},
    {'type': 'hidden', 'name': 'shopperLocale', 'value': 'fr'},
    {'type': 'hidden', 'name': 'shopperReference', 'value': 789},
    {'type': 'hidden', 'name': 'skinCode', 'value': 'cqQJKZpg'},
    {'type': 'hidden', 'name': 'countryCode', 'value': 'fr'},
]

ORDER_DATA = {
    'amount': 123,
    'basket_id': 456,
    'client_email': 'test@example.com',
    'client_id': 789,
    'currency_code': 'EUR',
    'country_code': 'fr',
    'description': 'Order #123',
    'order_id': 'ORD-123',
    'order_number': '00000000123',
    'return_url': TEST_RETURN_URL,
    'shopper_locale': 'fr',
}


class TestAdyenPaymentRequest(TestCase):

    @override_settings(ADYEN_ACTION_URL='foo')
    def test_form_action(self):
        """
        Test that the form action is properly fetched from the settings.
        """
        assert 'foo' == Scaffold().get_form_action(request=None)

    def test_form_fields_ok(self):
        """
        Test that the payment form fields list is properly built.
        """
        with freeze_time('2014-07-31 17:00:00'):  # Any datetime will do.
            fields_list = Scaffold().get_form_fields(request=None, order_data=ORDER_DATA)
            # Order doesn't matter, so normally we'd use a set. But Python doesn't do
            # sets of dictionaries, so we compare individually.
            assert len(fields_list) == len(EXPECTED_FIELDS_LIST)
            for field in fields_list:
                assert field in EXPECTED_FIELDS_LIST

    def test_form_fields_with_missing_mandatory_field(self):
        """
        Test that the proper exception is raised when trying
        to build a fields list with a missing mandatory field.
        """
        new_order_data = ORDER_DATA.copy()
        del new_order_data['amount']

        with self.assertRaises(MissingFieldException):
            Scaffold().get_form_fields(request=None, order_data=new_order_data)
