from unittest.mock import Mock
from copy import deepcopy

from django.test import TestCase

from adyen.facade import Facade
from adyen.gateway import MissingFieldException, InvalidTransactionException
from adyen.models import AdyenTransaction
from adyen.scaffold import Scaffold

from tests.test_notifications import AUTHORISED_PAYMENT_PARAMS_POST


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
TEST_IP_ADDRESS_HTTP_HEADER = 'HTTP_X_FORWARDED_FOR'


class TestAdyenPaymentRedirects(TestCase):
    """
    Test case that tests Adyen payment redirects (user redirected from Adyen to us)
    """

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
        # Valid IPv4 and IPv6 addresses
        valid_addresses = ['127.0.0.1', '192.168.12.34', '2001:0db8:85a3:0000:0000:8a2e:0370:7334']
        for address in valid_addresses:
            assert Facade._is_valid_ip_address(address)

        # Empty string, noise, IPv4 out of range, invalid IPv6-lookalike
        invalid_addresses = ['', 'TOTORO', '192.168.12.345', '2001::0234:C1ab::A0:aabc:003F']
        for address in invalid_addresses:
            assert not Facade._is_valid_ip_address(address)

    def test_get_origin_ip_address(self):
        """
        Make sure that the `_get_origin_ip_address()` method works with all
        the possible meaningful combinations of default and custom HTTP header
        names.
        """
        # With no specified ADYEN_IP_ADDRESS_HTTP_HEADER setting,
        # ensure we fetch the origin IP address in the REMOTE_ADDR
        # HTTP header.
        assert '127.0.0.1' == Facade()._get_origin_ip_address(self.request)

        # Check the return value is None if we have nothing
        # in the `REMOTE_ADDR` header.
        self.request.META.update({'REMOTE_ADDR': ''})
        assert Facade()._get_origin_ip_address(self.request) is None

        # Check the return value is None if we have no `REMOTE_ADDR`
        # header at all.
        del self.request.META['REMOTE_ADDR']
        assert Facade()._get_origin_ip_address(self.request) is None

        with self.settings(ADYEN_IP_ADDRESS_HTTP_HEADER=TEST_IP_ADDRESS_HTTP_HEADER):
            # Now we add the `HTTP_X_FORWARDED_FOR` header and
            # ensure it is used instead.
            self.request.META.update({
                'REMOTE_ADDR': '127.0.0.1',
                'HTTP_X_FORWARDED_FOR': '93.16.93.168'
            })
            assert '93.16.93.168' == Facade()._get_origin_ip_address(self.request)

            # Even if the default header is missing.
            del self.request.META['REMOTE_ADDR']
            assert '93.16.93.168' == Facade()._get_origin_ip_address(self.request)

            # And finally back to `None` if we have neither header.
            del self.request.META['HTTP_X_FORWARDED_FOR']
            assert Facade()._get_origin_ip_address(self.request) is None

    def test_handle_authorised_payment(self):
        self.request.GET = deepcopy(AUTHORISED_PAYMENT_PARAMS_GET)
        success, status, details = Scaffold().handle_payment_feedback(self.request)

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
            Scaffold().handle_payment_feedback(self.request)

        # So, let's try again with valid POST parameters.
        self.request.POST = deepcopy(AUTHORISED_PAYMENT_PARAMS_POST)
        success, status, details = Scaffold().handle_payment_feedback(self.request)

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
        ip_address = Facade()._get_origin_ip_address(self.request)
        self.assertIsNone(ip_address)

        # ... and finally make sure everything works as expected.
        success, status, details = Scaffold().handle_payment_feedback(self.request)

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
        success, status, __ = Scaffold().handle_payment_feedback(self.request)
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
        success, status, __ = Scaffold().handle_payment_feedback(self.request)
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
            Scaffold().handle_payment_feedback(self.request)

        # After the test, there are still no recorded transactions in the database.
        num_recorded_transactions = AdyenTransaction.objects.all().count()
        self.assertEqual(num_recorded_transactions, 0)
