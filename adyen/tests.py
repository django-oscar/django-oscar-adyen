# -*- coding: utf-8 -*-

from unittest.mock import Mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings

from oscar.core.loading import get_class
UnableToTakePayment = get_class('payment.exceptions', 'UnableToTakePayment')

from freezegun import freeze_time

from .gateway import MissingFieldException, InvalidTransactionException
from .models import AdyenTransaction
from .scaffold import Scaffold

TEST_IDENTIFIER = 'OscaroFR'
TEST_SECRET_KEY = 'oscaroscaroscaro'
TEST_ACTION_URL = 'https://test.adyen.com/hpp/select.shtml'
TEST_SKIN_CODE = 'cqQJKZpg'

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
        request.META = {
            'REMOTE_ADDR': '127.0.0.1',
        }
        self.request = request

    def test_handle_authorised_payment(self):

        # Before the test, there are no recorded transactions in the database
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)

        self.request.META['QUERY_STRING'] = AUTHORISED_PAYMENT_QUERY_STRING
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
