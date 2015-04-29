# -*- coding: utf-8 -*-

from copy import deepcopy
import six
from unittest.mock import Mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings

from freezegun import freeze_time

from adyen.gateway import MissingFieldException, InvalidTransactionException
from adyen.models import AdyenTransaction
from adyen.scaffold import Scaffold
from adyen.facade import Facade


TEST_IDENTIFIER = 'OscaroFR'
TEST_SECRET_KEY = 'oscaroscaroscaro'
TEST_ACTION_URL = 'https://test.adyen.com/hpp/select.shtml'
TEST_SKIN_CODE = 'cqQJKZpg'
TEST_IP_ADDRESS_HTTP_HEADER = 'HTTP_X_FORWARDED_FOR'

TEST_RETURN_URL = 'https://www.example.com/checkout/return/adyen/'

TEST_FROZEN_TIME = '2014-07-31 17:00:00'

EXPECTED_FIELDS_LIST = [
    {'type': 'hidden', 'name': 'currencyCode', 'value': 'EUR'},
    {'type': 'hidden', 'name': 'merchantAccount', 'value': TEST_IDENTIFIER},
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

AUTHORISED_PAYMENT_PARAMS_GET = {
    'authResult': 'AUTHORISED',
    'merchantReference': 'WVubjVRFOTPBsLNy33zqliF-vmc:109:00000109',
    'merchantReturnData': '13894',
    'merchantSig': '99Y+9EiSuT6W4rd/M3zg/wwwRjw=',
    'paymentMethod': 'visa',
    'pspReference': '8814136447235922',
    'shopperLocale': 'en_GB',
    'skinCode': '4d72uQqA',
}

AUTHORISED_PAYMENT_PARAMS_POST = {
    'currency': 'EUR',
    'eventCode': 'AUTHORISATION',
    'live': 'false',
    'eventDate': '2014-10-18T17:00:00.00Z',
    'merchantAccountCode': 'OscaroBE',
    'merchantReference': '789:456:00000000123',
    'operations': 'CANCEL,CAPTURE,REFUND',
    'originalReference': '',
    'paymentMethod': 'visa',
    'pspReference': '7914120802434172',
    'reason': '32853:1111:6/2016',
    'success': 'true',
    'value': '21714',
}

CANCELLED_PAYMENT_PARAMS = {
    'authResult': 'CANCELLED',
    'merchantReference': 'WVubjVRFOTPBsLNy33zqliF-vmc:110:00000110',
    'merchantReturnData': '13894',
    'merchantSig': 'AMkos00Nn+bTgS3Ndm2bgnRBj1c=',
    'shopperLocale': 'en_GB',
    'skinCode': '4d72uQqA',
}

REFUSED_PAYMENT_PARAMS = {
    'authResult': 'REFUSED',
    'merchantReference': 'WVubjVRFOTPBsLNy33zqliF-vmc:110:00000110',
    'merchantReturnData': '13894',
    'merchantSig': '1fFM0LaC0uhsN3L/C9nddUeMiyw=',
    'paymentMethod': 'visa',
    'pspReference': '8814136452896857',
    'shopperLocale': 'en_GB',
    'skinCode': '4d72uQqA',
}

TAMPERED_PAYMENT_PARAMS = {
    'authResult': 'AUTHORISED',
    'merchantReference': 'WVubjVRFOTPBsLNy33zqliF-vmc:109:00000109',
    'merchantReturnData': '13894',
    'merchantSig': '14M4N3V1LH4X0RZ',
    'paymentMethod': 'visa',
    'pspReference': '8814136447235922',
    'shopperLocale': 'en_GB',
    'skinCode': '4d72uQqA',
}


@override_settings(
    ADYEN_IDENTIFIER=TEST_IDENTIFIER,
    ADYEN_SECRET_KEY=TEST_SECRET_KEY,
    ADYEN_ACTION_URL=TEST_ACTION_URL,
    ADYEN_SKIN_CODE=TEST_SKIN_CODE,
)
class AdyenTestCase(TestCase):

    def setUp(self):
        super().setUp()

        self.order_data = {
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
        self.scaffold = Scaffold(self.order_data)


class TestAdyenPaymentRequest(AdyenTestCase):

    @override_settings(ADYEN_ACTION_URL=TEST_ACTION_URL)
    def test_form_action(self):
        """
        Test that the form action is properly fetched from the settings.
        """
        action_url = self.scaffold.get_form_action()
        self.assertEqual(action_url, TEST_ACTION_URL)

        # If the setting is missing, a proper exception is raised
        del settings.ADYEN_ACTION_URL
        with self.assertRaises(ImproperlyConfigured):
            self.scaffold.get_form_action()

    def test_form_fields_ok(self):
        """
        Test that the payment form fields are properly built.
        """
        with freeze_time(TEST_FROZEN_TIME):
            form_fields = self.scaffold.get_form_fields()
            for field_spec in EXPECTED_FIELDS_LIST:
                field = '<input type="%s" name="%s" value="%s">' % (
                    field_spec.get('type'),
                    field_spec.get('name'),
                    field_spec.get('value'),
                )
                self.assertIn(field, form_fields)

    def test_form_fields_list_ok(self):
        """
        Test that the payment form fields list is properly built.
        """
        with freeze_time(TEST_FROZEN_TIME):
            fields_list = self.scaffold.get_form_fields_list()
            self.assertEqual(len(fields_list), len(EXPECTED_FIELDS_LIST))
            for field in fields_list:
                self.assertIn(field, EXPECTED_FIELDS_LIST)

    def test_form_fields_list_with_missing_mandatory_field(self):
        """
        Test that the proper exception is raised when trying
        to build a fields list with a missing mandatory field.
        """
        del self.order_data['amount']
        scaffold = Scaffold(self.order_data)
        with self.assertRaises(MissingFieldException):
            scaffold.get_form_fields_list()


class TestAdyenPaymentResponse(AdyenTestCase):

    def setUp(self):
        super().setUp()
        request = Mock()
        request.method = 'GET'

        # Most tests use unproxied requests, the case of proxied ones
        # is unit-tested by the `test_get_origin_ip_address` method.
        request.META = {
            'REMOTE_ADDR': '127.0.0.1',
        }

        self.request = request

    def test_is_valid_ip_address(self):

        # The empty string is not a valid IP address.
        ip_address = ''
        self.assertFalse(Facade._is_valid_ip_address(ip_address))

        # A kinda random string is not a valid IP address.
        ip_address = 'TOTORO'
        self.assertFalse(Facade._is_valid_ip_address(ip_address))

        # These are valid IP addresses.
        ip_address = '127.0.0.1'
        self.assertTrue(Facade._is_valid_ip_address(ip_address))
        ip_address = '192.168.12.34'
        self.assertTrue(Facade._is_valid_ip_address(ip_address))

        # This one is out of the valid ranges.
        ip_address = '192.168.12.345'
        self.assertFalse(Facade._is_valid_ip_address(ip_address))

        # This one is a valid IPv6 address.
        ip_address = '2001:0db8:85a3:0000:0000:8a2e:0370:7334'
        self.assertTrue(Facade._is_valid_ip_address(ip_address))

        # This one is an invalid IPv6 address.
        ip_address = '2001::0234:C1ab::A0:aabc:003F'
        self.assertFalse(Facade._is_valid_ip_address(ip_address))

    def test_get_origin_ip_address(self):
        """
        Make sure that the `_get_origin_ip_address()` method works with all
        the possible meaningful combinations of default and custom HTTP header
        names.
        """

        # With no specified ADYEN_IP_ADDRESS_HTTP_HEADER setting,
        # ensure we fetch the origin IP address in the REMOTE_ADDR
        # HTTP header.
        ip_address = Facade._get_origin_ip_address(self.request)
        self.assertEqual(ip_address, '127.0.0.1')
        if six.PY3:
            self.assertEqual(type(ip_address), str)

        # Check the return value is None if we have nothing
        # in the `REMOTE_ADDR` header.
        self.request.META.update({'REMOTE_ADDR': ''})
        ip_address = Facade._get_origin_ip_address(self.request)
        self.assertIsNone(ip_address)

        # Check the return value is None if we have no `REMOTE_ADDR`
        # header at all.
        del self.request.META['REMOTE_ADDR']
        ip_address = Facade._get_origin_ip_address(self.request)
        self.assertIsNone(ip_address)

        with self.settings(ADYEN_IP_ADDRESS_HTTP_HEADER=TEST_IP_ADDRESS_HTTP_HEADER):

            # Now we add the `HTTP_X_FORWARDED_FOR` header and
            # ensure it is used instead.
            self.request.META.update({
                'REMOTE_ADDR': '127.0.0.1',
                'HTTP_X_FORWARDED_FOR': '93.16.93.168'
            })
            ip_address = Facade._get_origin_ip_address(self.request)
            self.assertEqual(ip_address, '93.16.93.168')
            if six.PY3:
                self.assertEqual(type(ip_address), str)

            # Even if the default header is missing.
            del self.request.META['REMOTE_ADDR']
            ip_address = Facade._get_origin_ip_address(self.request)
            self.assertEqual(ip_address, '93.16.93.168')
            if six.PY3:
                self.assertEqual(type(ip_address), str)

            # And finally back to `None` if we have neither header.
            del self.request.META['HTTP_X_FORWARDED_FOR']
            ip_address = Facade._get_origin_ip_address(self.request)
            self.assertIsNone(ip_address)

    def test_handle_authorised_payment(self):

        # Before the test, there are no recorded transactions in the database.
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        self.request.GET = deepcopy(AUTHORISED_PAYMENT_PARAMS_GET)
        success, status, details = self.scaffold.check_payment_outcome(self.request)

        self.assertTrue(success)
        self.assertEqual(status, Scaffold.PAYMENT_STATUS_ACCEPTED)
        self.assertEqual(details.get('amount'), 13894)
        self.assertEqual(details.get('ip_address'), '127.0.0.1')
        self.assertEqual(details.get('method'), 'adyen')
        self.assertEqual(details.get('psp_reference'), '8814136447235922')
        self.assertEqual(details.get('status'), 'AUTHORISED')

        # After calling `check_payment_outcome`, there are still no recorded
        # transactions in the database.
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        self.request.GET = deepcopy(AUTHORISED_PAYMENT_PARAMS_GET)
        success, status, details = self.scaffold.handle_payment_feedback(self.request)

        self.assertTrue(success)
        self.assertEqual(status, Scaffold.PAYMENT_STATUS_ACCEPTED)
        self.assertEqual(details.get('amount'), 13894)
        self.assertEqual(details.get('ip_address'), '127.0.0.1')
        self.assertEqual(details.get('method'), 'adyen')
        self.assertEqual(details.get('psp_reference'), '8814136447235922')
        self.assertEqual(details.get('status'), 'AUTHORISED')

        # After calling `handle_payment_feedback` there is one authorised
        # transaction and no refused transaction in the database.
        num_authorised_transactions = AdyenTransaction.objects.filter(status='AUTHORISED').count()
        self.assertEqual(num_authorised_transactions, 1)
        num_refused_transactions = AdyenTransaction.objects.filter(status='REFUSED').count()
        self.assertEqual(num_refused_transactions, 0)

        # We delete the previously recorded AdyenTransaction.
        AdyenTransaction.objects.filter(status='AUTHORISED').delete()

        # We now test with POST instead of GET.
        self.request.method = 'POST'
        self.request.POST = deepcopy(AUTHORISED_PAYMENT_PARAMS_GET)
        self.request.GET = None

        # This is going to fail because the mandatory fields are not the same
        # for GET and POST requests.
        with self.assertRaises(MissingFieldException):
            self.scaffold.handle_payment_feedback(self.request)

        # So, let's try again with valid POST parameters.
        self.request.POST = deepcopy(AUTHORISED_PAYMENT_PARAMS_POST)
        success, status, details = self.scaffold.handle_payment_feedback(self.request)

        self.assertTrue(success)
        self.assertEqual(status, Scaffold.PAYMENT_STATUS_ACCEPTED)
        self.assertEqual(details.get('amount'), 21714)
        self.assertEqual(details.get('ip_address'), '127.0.0.1')
        self.assertEqual(details.get('method'), 'adyen')
        self.assertEqual(details.get('psp_reference'), '7914120802434172')
        self.assertEqual(details.get('status'), 'AUTHORISED')

        # After calling `handle_payment_feedback` there is one authorised
        # transaction and no refused transaction in the database.
        num_authorised_transactions = AdyenTransaction.objects.filter(status='AUTHORISED').count()
        self.assertEqual(num_authorised_transactions, 1)
        num_refused_transactions = AdyenTransaction.objects.filter(status='REFUSED').count()
        self.assertEqual(num_refused_transactions, 0)

    def test_handle_authorized_payment_if_no_ip_address_was_found(self):
        """
        A slight variation on the previous test.
        We just want to ensure that the backend does not crash if we haven't
        been able to find a reliable origin IP address.
        """
        self.request.GET = deepcopy(AUTHORISED_PAYMENT_PARAMS_GET)

        # Before the test, there are no recorded transactions in the database.
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        # We alter the request so no IP address will be found...
        del self.request.META['REMOTE_ADDR']

        # ... double-check that the IP address is, therefore, `None` ...
        ip_address = Facade._get_origin_ip_address(self.request)
        self.assertIsNone(ip_address)

        # ... and finally make sure everything works as expected.
        success, status, details = self.scaffold.handle_payment_feedback(self.request)

        self.assertTrue(success)
        self.assertEqual(status, Scaffold.PAYMENT_STATUS_ACCEPTED)
        self.assertEqual(details.get('amount'), 13894)
        self.assertEqual(details.get('method'), 'adyen')
        self.assertEqual(details.get('psp_reference'), '8814136447235922')
        self.assertEqual(details.get('status'), 'AUTHORISED')
        self.assertIsNone(details.get('ip_address'))

        # After the test there's one authorised transaction and no refused transaction in the DB.
        num_authorised_transactions = AdyenTransaction.objects.filter(status='AUTHORISED').count()
        self.assertEqual(num_authorised_transactions, 1)
        num_refused_transactions = AdyenTransaction.objects.filter(status='REFUSED').count()
        self.assertEqual(num_refused_transactions, 0)

    def test_handle_cancelled_payment(self):

        # Before the test, there are no recorded transactions in the database.
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        self.request.GET = deepcopy(CANCELLED_PAYMENT_PARAMS)
        success, status, __ = self.scaffold.handle_payment_feedback(self.request)
        self.assertFalse(success)
        self.assertEqual(status, Scaffold.PAYMENT_STATUS_CANCELLED)

        # After the test there's one cancelled transaction and no authorised transaction in the DB.
        num_authorised_transactions = AdyenTransaction.objects.filter(status='AUTHORISED').count()
        self.assertEqual(num_authorised_transactions, 0)
        num_cancelled_transactions = AdyenTransaction.objects.filter(status='CANCELLED').count()
        self.assertEqual(num_cancelled_transactions, 1)

    def test_handle_refused_payment(self):

        # Before the test, there are no recorded transactions in the database.
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        self.request.GET = deepcopy(REFUSED_PAYMENT_PARAMS)
        success, status, __ = self.scaffold.handle_payment_feedback(self.request)
        self.assertFalse(success)
        self.assertEqual(status, Scaffold.PAYMENT_STATUS_REFUSED)

        # After the test there's one refused transaction and no authorised transaction in the DB.
        num_authorised_transactions = AdyenTransaction.objects.filter(status='AUTHORISED').count()
        self.assertEqual(num_authorised_transactions, 0)
        num_refused_transactions = AdyenTransaction.objects.filter(status='REFUSED').count()
        self.assertEqual(num_refused_transactions, 1)

    def test_handle_tampered_payment(self):

        # Before the test, there are no recorded transactions in the database.
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        self.request.GET = deepcopy(TAMPERED_PAYMENT_PARAMS)
        with self.assertRaises(InvalidTransactionException):
            self.scaffold.handle_payment_feedback(self.request)

        # After the test, there are still no recorded transactions in the database.
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

    def test_assess_notification_relevance(self):

        self.request.method = 'POST'

        # If this is an `AUTHORISATION` request targeting the proper platform,
        # we should both process and acknowledge it.
        self.request.POST = deepcopy(AUTHORISED_PAYMENT_PARAMS_POST)
        must_process, must_ack = self.scaffold.assess_notification_relevance(self.request)
        self.assertTupleEqual((must_process, must_ack), (True, True))

        # If there is a mismatch between the request origin and target platforms,
        # we should just let it be.
        self.request.POST['live'] = 'true'
        must_process, must_ack = self.scaffold.assess_notification_relevance(self.request)
        self.assertTupleEqual((must_process, must_ack), (False, False))

        self.request.POST['live'] = 'false'
        with self.settings(ADYEN_ACTION_URL='https://live.adyen.com/hpp/select.shtml'):
            must_process, must_ack = self.scaffold.assess_notification_relevance(self.request)
            self.assertTupleEqual((must_process, must_ack), (False, False))

        # If this is not an `AUTHORISATION` request, we should acknowledge it
        # but not try to process it.
        self.request.POST['eventCode'] = 'REPORT_AVAILABLE'
        must_process, must_ack = self.scaffold.assess_notification_relevance(self.request)
        self.assertTupleEqual((must_process, must_ack), (False, True))
