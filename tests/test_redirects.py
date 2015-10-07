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
    Test case that tests Adyen payment redirects (user redirected from Adyen to us).

    Note that notifications and redirects are pretty similar and share a lot of
    common code. So those tests will actually test a lot of code for notifications
    as well. In an ideal world, we'd split things up to check the shared code individually.
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

    def test_signing_is_enforced(self):
        """
        Test that the supplied signature (in field merchantSig) is checked and
        notifications are ignored when the signature doesn't match.

        In an ideal world, our other tests would ignore the signature checking
        because it's annoying to have to alter the sig when altering the fake
        data. Maik gets valid signatures by adding a print(expected_hash) to
        PaymentRedirection.validate.
        """
        fake_signature = copy(AUTHORISED_PAYMENT_PARAMS_GET)
        fake_signature['merchantSig'] = '14M4N3V1LH4X0RZ'
        signature_none = copy(AUTHORISED_PAYMENT_PARAMS_GET)
        signature_none ['merchantSig'] = None
        signature_empty = copy(AUTHORISED_PAYMENT_PARAMS_GET)
        signature_empty['merchantSig'] = ''

        for tampered_data in [fake_signature, signature_empty, signature_none]:
            request = MockRequest(tampered_data)
            try:
                Scaffold().handle_payment_feedback(request)
            except (InvalidTransactionException, MissingFieldException):
                pass
            else:
                raise AssertionError("Should've raised an exception, but didn't")

        # Make sure we haven't recorded any of those faulty transactions.
        # That way, nobody can fill up our database!
        assert not AdyenTransaction.objects.exists()

    def test_handle_error_payment(self):
        # This is actual data received from Adyen causing a bug.
        # The merchantSig hash was replaced to pass hashing with the test secret key.
        request = MockRequest({
            'authResult': 'ERROR',
            'merchantReference': '09016057',
            'merchantReturnData': '29232',
            'merchantSig': 'Y2lpKZPCOpK7WAlCVSgUQcJ9+xQ=',
            'paymentMethod': 'visa',
            'shopperLocale': 'fr',
            'skinCode': '4d72uQqA',
        })

        success, status, __ = Scaffold().handle_payment_feedback(request)
        assert (not success) and (status == Scaffold.PAYMENT_STATUS_ERROR)

        assert AdyenTransaction.objects.filter(status='ERROR').count() == 1

    def test_handle_pending_payment(self):
        # Modified actual data (see test_handle_error_payment)
        request = MockRequest({
            'authResult': 'PENDING',
            'merchantReference': '09016057',
            'merchantReturnData': '29232',
            'merchantSig': 'QTUYO2Bk9CbVCfUztp+MuCFe8do=',
            'paymentMethod': 'visa',
            'shopperLocale': 'fr',
            'skinCode': '4d72uQqA',
        })

        success, status, __ = Scaffold().handle_payment_feedback(request)
        assert (not success) and (status == Scaffold.PAYMENT_STATUS_PENDING)

        assert AdyenTransaction.objects.filter(status='PENDING').count() == 1
