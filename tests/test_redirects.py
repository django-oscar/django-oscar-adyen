from copy import copy
from django.test import TestCase

from adyen.facade import Facade
from adyen.gateway import MissingFieldException, InvalidTransactionException
from adyen.models import AdyenTransaction
from adyen.scaffold import Scaffold

from tests import MockRequest
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


class TestAdyenPaymentRedirects(TestCase):
    """
    Test case that tests Adyen payment redirects (user redirected from Adyen to us)
    """

    def test_handle_authorised_payment(self):
        request = MockRequest(AUTHORISED_PAYMENT_PARAMS_GET)
        success, status, details = Scaffold().handle_payment_feedback(request)

        assert success
        assert status == Scaffold.PAYMENT_STATUS_ACCEPTED
        assert details['amount'] == 13894
        assert details['ip_address'] == '127.0.0.1'
        assert details['method'] == 'adyen'
        assert details['psp_reference'] == '8814136447235922'
        assert details['status'] == 'AUTHORISED'

        # After calling `handle_payment_feedback` there is one authorised
        # transaction and no refused transaction in the database.
        assert AdyenTransaction.objects.filter(status='AUTHORISED').count() == 1
        assert AdyenTransaction.objects.filter(status='REFUSED').count() == 0

        # We delete the previously recorded AdyenTransaction.
        AdyenTransaction.objects.filter(status='AUTHORISED').delete()

        # We now test with POST instead of GET.
        request = MockRequest(AUTHORISED_PAYMENT_PARAMS_GET, method='POST')

        # This is going to fail because the mandatory fields are not the same
        # for GET and POST requests.
        with self.assertRaises(MissingFieldException):
            Scaffold().handle_payment_feedback(request)

        # So, let's try again with valid POST parameters.
        request = MockRequest(AUTHORISED_PAYMENT_PARAMS_POST, method='POST')
        success, status, details = Scaffold().handle_payment_feedback(request)

        assert success
        assert status == Scaffold.PAYMENT_STATUS_ACCEPTED
        assert details['amount'] == 21714
        assert details['ip_address'] == '127.0.0.1'
        assert details['method'] == 'adyen'
        assert details['psp_reference'] == '7914120802434172'
        assert details['status'] == 'AUTHORISED'

        # After calling `handle_payment_feedback` there is one authorised
        # transaction and no refused transaction in the database.
        assert AdyenTransaction.objects.filter(status='AUTHORISED').count() == 1
        assert AdyenTransaction.objects.filter(status='REFUSED').count() == 0

    def test_handle_authorized_payment_if_no_ip_address_was_found(self):
        """
        A slight variation on the previous test.
        We just want to ensure that the backend does not crash if we haven't
        been able to find a reliable origin IP address.
        """
        # We create a request so no IP address will be found...
        request = MockRequest(AUTHORISED_PAYMENT_PARAMS_GET, remote_address=None)

        # ... double-check that the IP address is, therefore, `None` ...
        assert Facade()._get_origin_ip_address(request) is None

        # ... and finally make sure everything works as expected.
        success, status, details = Scaffold().handle_payment_feedback(request)

        assert success
        assert details['ip_address'] is None

        # After the test there's one authorised transaction and no refused transaction in the DB.
        assert AdyenTransaction.objects.filter(status='AUTHORISED').count() == 1
        assert AdyenTransaction.objects.filter(status='REFUSED').count() == 0

    def test_handle_cancelled_payment(self):
        request = MockRequest({
            'authResult': 'CANCELLED',
            'merchantReference': 'WVubjVRFOTPBsLNy33zqliF-vmc:110:00000110',
            'merchantReturnData': '13894',
            'merchantSig': 'AMkos00Nn+bTgS3Ndm2bgnRBj1c=',
            'shopperLocale': 'en_GB',
            'skinCode': '4d72uQqA',
        })
        success, status, __ = Scaffold().handle_payment_feedback(request)
        assert (not success) and (status == Scaffold.PAYMENT_STATUS_CANCELLED)

        # After the test there's one cancelled transaction and no authorised transaction in the DB.
        assert AdyenTransaction.objects.filter(status='AUTHORISED').count() == 0
        assert AdyenTransaction.objects.filter(status='CANCELLED').count() == 1

    def test_handle_refused_payment(self):
        request = MockRequest({
            'authResult': 'REFUSED',
            'merchantReference': 'WVubjVRFOTPBsLNy33zqliF-vmc:110:00000110',
            'merchantReturnData': '13894',
            'merchantSig': '1fFM0LaC0uhsN3L/C9nddUeMiyw=',
            'paymentMethod': 'visa',
            'pspReference': '8814136452896857',
            'shopperLocale': 'en_GB',
            'skinCode': '4d72uQqA',
        })

        success, status, __ = Scaffold().handle_payment_feedback(request)
        assert (not success) and (status == Scaffold.PAYMENT_STATUS_REFUSED)

        # After the test there's one refused transaction and no authorised transaction in the DB.
        assert AdyenTransaction.objects.filter(status='AUTHORISED').count() == 0
        assert AdyenTransaction.objects.filter(status='REFUSED').count() == 1

    def test_handle_tampered_payment(self):
        tampered_data = copy(AUTHORISED_PAYMENT_PARAMS_GET)
        tampered_data['merchantSig'] = '14M4N3V1LH4X0RZ'
        request = MockRequest(tampered_data)

        with self.assertRaises(InvalidTransactionException):
            Scaffold().handle_payment_feedback(request)

        # After the test, there are still no recorded transactions in the database.
        assert not AdyenTransaction.objects.exists()
