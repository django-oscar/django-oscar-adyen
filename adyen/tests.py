# -*- coding: utf-8 -*-

from unittest.mock import Mock

from freezegun import freeze_time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings

from oscar.apps.payment.exceptions import UnableToTakePayment

from .gateway import MissingFieldException, InvalidTransactionException
from .models import AdyenTransaction
from .scaffold import Scaffold
from .facade import Facade

TEST_IDENTIFIER = 'OscaroFR'
TEST_SECRET_KEY = 'oscaroscaroscaro'
TEST_ACTION_URL = 'https://test.adyen.com/hpp/select.shtml'
TEST_SKIN_CODE = 'cqQJKZpg'
TEST_IP_ADDRESS_HTTP_HEADER = 'HTTP_X_FORWARDED_FOR'

TEST_RETURN_URL = 'https://www.test.com/checkout/return/adyen/'

TEST_FROZEN_TIME = '2014-07-31 17:00:00'

EXPECTED_FIELDS_LIST = [
    {'type': 'hidden', 'name': 'currencyCode', 'value': 'EUR'},
    {'type': 'hidden', 'name': 'sessionValidity', 'value': '2014-07-31T17:20:00Z'},
    {'type': 'hidden', 'name': 'skinCode', 'value': 'cqQJKZpg'},
    {'type': 'hidden', 'name': 'resURL', 'value': TEST_RETURN_URL},
    {'type': 'hidden', 'name': 'merchantReference', 'value': 'ORD-123'},
    {'type': 'hidden', 'name': 'paymentAmount', 'value': 123},
    {'type': 'hidden', 'name': 'shopperEmail', 'value': 'test@test.com'},
    {'type': 'hidden', 'name': 'merchantAccount', 'value': TEST_IDENTIFIER},
    {'type': 'hidden', 'name': 'merchantReturnData', 'value': 123},
    {'type': 'hidden', 'name': 'shipBeforeDate', 'value': '2014-08-30'},
    {'type': 'hidden', 'name': 'merchantSig', 'value': 'qmgTX6kGPLmDNLf3W1e1oR7g7h8='},
    {'type': 'hidden', 'name': 'shopperReference', 'value': 123},
]

AUTHORISED_PAYMENT_QUERY_STRING = ('merchantReference=40100020137&skinCode=cqQJKZpg'
                                   '&shopperLocale=en_GB&paymentMethod=visa&authResult=AUTHORISED'
                                   '&pspReference=8614068242050184&merchantReturnData=67864'
                                   '&merchantSig=k5Ji9eQ5kSoLdEHfydfDognnsoo=')

CANCELLED_PAYMENT_QUERY_STRING = ('merchantReference=00000045&skinCode=cqQJKZpg'
                                  '&shopperLocale=en_GB&authResult=CANCELLED'
                                  '&merchantReturnData=25956'
                                  '&merchantSig=Z5s7N0AwQ5BuK4p05tAzdzrE3K4=')

REFUSED_PAYMENT_QUERY_STRING = ('merchantReference=40100020139&skinCode=cqQJKZpg'
                                '&shopperLocale=en_GB&paymentMethod=visa&authResult=REFUSED'
                                '&pspReference=8614068251598198&merchantReturnData=67864'
                                '&merchantSig=3KI5SiHHkftRwzoM7gue4D0aIaY=')

TAMPERED_QUERY_STRING = ('merchantReference=40100020135&skinCode=cqQJKZpg'
                         '&shopperLocale=en_GB&paymentMethod=visa&authResult=AUTHORISED'
                         '&pspReference=8614068228971221&merchantReturnData=67864'
                         '&merchantSig=14M4N3V1LH4X0RZ')


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
            'order_id': 'ORD-123',
            'client_id': 123,
            'client_email': 'test@test.com',
            'amount': 123,
            'currency_code': 'EUR',
            'description': 'Order #123',
            'return_url': TEST_RETURN_URL,
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

        # Most tests use unproxied requests, the case of proxied ones
        # is unit-tested by the `test_get_origin_ip_address` method.
        request.META = {
            'REMOTE_ADDR': '127.0.0.1',
        }

        self.request = request

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

            # Even if the default header is missing.
            del self.request.META['REMOTE_ADDR']
            ip_address = Facade._get_origin_ip_address(self.request)
            self.assertEqual(ip_address, '93.16.93.168')

            # And finally back to `None` if we have neither header.
            del self.request.META['HTTP_X_FORWARDED_FOR']
            ip_address = Facade._get_origin_ip_address(self.request)
            self.assertIsNone(ip_address)

    def test_handle_authorised_payment(self):
        self.request.META['QUERY_STRING'] = AUTHORISED_PAYMENT_QUERY_STRING

        # Before the test, there are no recorded transactions in the database
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        authorised, info = self.scaffold.handle_payment_feedback(self.request)
        self.assertTrue(authorised)
        self.assertEqual(info.get('amount'), 67864)
        self.assertEqual(info.get('method'), 'adyen')
        self.assertEqual(info.get('ip_address'), '127.0.0.1')
        self.assertEqual(info.get('status'), 'AUTHORISED')
        self.assertEqual(info.get('reference'), '8614068242050184')

        # After the test there's one authorised transaction and no refused transaction in the DB
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
        self.request.META['QUERY_STRING'] = AUTHORISED_PAYMENT_QUERY_STRING

        # Before the test, there are no recorded transactions in the database
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        # We alter the request so no IP address will be found...
        del self.request.META['REMOTE_ADDR']

        # ... double-check that the IP address is, therefore, `None` ...
        ip_address = Facade._get_origin_ip_address(self.request)
        self.assertIsNone(ip_address)

        # ... and finally make sure everything works as expected.
        authorised, info = self.scaffold.handle_payment_feedback(self.request)
        self.assertTrue(authorised)
        self.assertEqual(info.get('amount'), 67864)
        self.assertEqual(info.get('method'), 'adyen')
        self.assertIsNone(info.get('ip_address'))
        self.assertEqual(info.get('status'), 'AUTHORISED')
        self.assertEqual(info.get('reference'), '8614068242050184')

        # After the test there's one authorised transaction and no refused transaction in the DB
        num_authorised_transactions = AdyenTransaction.objects.filter(status='AUTHORISED').count()
        self.assertEqual(num_authorised_transactions, 1)
        num_refused_transactions = AdyenTransaction.objects.filter(status='REFUSED').count()
        self.assertEqual(num_refused_transactions, 0)

    def test_handle_cancelled_payment(self):

        # Before the test, there are no recorded transactions in the database
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        self.request.META['QUERY_STRING'] = CANCELLED_PAYMENT_QUERY_STRING

        try:
            from oscar.apps.payment.exceptions import PaymentCancelled
        except ImportError:
            from oscar.apps.payment.exceptions import UnableToTakePayment as PaymentCancelled

        with self.assertRaises(PaymentCancelled):
            self.scaffold.handle_payment_feedback(self.request)

        # After the test there's one cancelled transaction and no authorised transaction in the DB
        num_authorised_transactions = AdyenTransaction.objects.filter(status='AUTHORISED').count()
        self.assertEqual(num_authorised_transactions, 0)
        num_cancelled_transactions = AdyenTransaction.objects.filter(status='CANCELLED').count()
        self.assertEqual(num_cancelled_transactions, 1)

    def test_handle_refused_payment(self):

        # Before the test, there are no recorded transactions in the database
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        self.request.META['QUERY_STRING'] = REFUSED_PAYMENT_QUERY_STRING
        with self.assertRaises(UnableToTakePayment):
            self.scaffold.handle_payment_feedback(self.request)

        # After the test there's one refused transaction and no authorised transaction in the DB
        num_authorised_transactions = AdyenTransaction.objects.filter(status='AUTHORISED').count()
        self.assertEqual(num_authorised_transactions, 0)
        num_refused_transactions = AdyenTransaction.objects.filter(status='REFUSED').count()
        self.assertEqual(num_refused_transactions, 1)

    def test_handle_tampered_payment(self):

        # Before the test, there are no recorded transactions in the database
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        self.request.META['QUERY_STRING'] = TAMPERED_QUERY_STRING
        with self.assertRaises(InvalidTransactionException):
            self.scaffold.handle_payment_feedback(self.request)

        # After the test, there are still no recorded transactions in the database
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)
