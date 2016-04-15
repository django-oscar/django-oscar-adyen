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

        # Make sure no extra signature fields are given when not required.
        assert 'billingAddressSig' not in result, (
            'The billingAddressSig must not be generated when '
            'billingAddress.* fields are not provided.')
        assert 'deliveryAddressSig' not in result, (
            'The deliveryAddressSig must not be generated when '
            'deliveryAddress.* fields are not provided.')
        assert 'shopperSig' not in result, (
            'The shopperSig must not be generated when '
            'shopper.* fields are not provided.')

    def test_sign_with_shopper(self):
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
        initial_signature = result['merchantSig']

        fields.update({
            'shopper.firstName': 'First Name',
            'shopper.lastName': 'Last Name',
        })

        # Regenerate signatures
        result = signer.sign(fields)
        assert result['merchantSig'] == initial_signature, (
            'Signature must not be modified with new shopper.* fields')
        assert 'shopperSig' in result, (
            'We expect a shopperSig since shopper.* fields are given.')
        assert result['shopperSig'] == 'CQoNDSMwBbcKAzVgyJqdEWvKDBI='

        initial_shopper_sig = result['shopperSig']

        # Add a shopper type: the initial signature is modified
        fields.update({
            'shopperType': '2'  # Not visible
        })
        result = signer.sign(fields)
        assert result['merchantSig'] != initial_signature, (
            'Signature must be modified with shopperType field added.')
        assert result['merchantSig'] == '1C4z/P7viArcR/ocW1qtz5iSBa0='

        assert result['shopperSig'] == initial_shopper_sig, (
            'shopperSig must not be modified with shopperType field added')

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
