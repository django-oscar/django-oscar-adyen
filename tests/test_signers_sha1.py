import unittest

from adyen.signers import HMACSha1


class TestHMACSha1(unittest.TestCase):
    def test_sign(self):
        secret_key = 'oscaroscaroscaro'
        signer = HMACSha1(secret_key)

        fields = {
            'merchantReturnData': 123,
            'paymentAmount': 123,
            'countryCode': 'fr',
            'currencyCode': 'EUR',
            'sessionValidity': '2014-07-31T17:20:00Z',
            'merchantReference': '00000000123',
            'shopperEmail': 'test@example.com',
            'shopperLocale': 'fr',
            'shopperReference': 789,
            'resURL': 'https://www.example.com/checkout/return/adyen/',
            'shipBeforeDate': '2014-08-30',
            'skinCode': 'cqQJKZpg',
            'merchantAccount': 'OscaroFR'
        }

        result = signer.sign(fields)

        assert 'merchantSig' in result
        assert result['merchantSig'] == 'kKvzRvx7wiPLrl8t8+owcmMuJZM='

    def test_verify_return_authorised(self):
        secret_key = 'oscaroscaroscaro'
        signer = HMACSha1(secret_key)

        fields = {
            'authResult': 'AUTHORISED',
            'merchantReference': 'WVubjVRFOTPBsLNy33zqliF-vmc:109:00000109',
            'merchantReturnData': '13894',
            'merchantSig': '99Y+9EiSuT6W4rd/M3zg/wwwRjw=',
            'paymentMethod': 'visa',
            'pspReference': '8814136447235922',
            'shopperLocale': 'en_GB',
            'skinCode': '4d72uQqA',
        }

        assert signer.verify(fields) is True

    def test_verify_return_error(self):
        secret_key = 'oscaroscaroscaro'
        signer = HMACSha1(secret_key)

        fields = {
            'authResult': 'ERROR',
            'merchantReference': '09016057',
            'merchantReturnData': '29232',
            'merchantSig': 'Y2lpKZPCOpK7WAlCVSgUQcJ9+xQ=',
            'paymentMethod': 'visa',
            'shopperLocale': 'fr',
            'skinCode': '4d72uQqA',
        }

        assert signer.verify(fields) is True
