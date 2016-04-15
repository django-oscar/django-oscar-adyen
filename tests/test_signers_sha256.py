import unittest

from adyen.signers import HMACSha256


class TestHMACSha256(unittest.TestCase):
    def test_sign(self):
        """Make sure the sign method works as expected.

        The test data are taken from the Adyen documentation.
        See https://docs.adyen.com/manuals/hpp-manual#pythonhmacsignature
        for more details.
        """
        secret_key = (
            '4468D9782DEF54FCD706C9100C71EC43932B1EBC2ACF6BA0560C05AAA7550C48')
        signer = HMACSha256(secret_key)
        fields = {
            'merchantAccount': 'TestMerchant', 
            'currencyCode': 'EUR', 
            'paymentAmount': '199', 
            'sessionValidity': '2015-06-25T10:31:06Z', 
            'shipBeforeDate': '2015-07-01', 
            'shopperLocale': 'en_GB', 
            'merchantReference': 'SKINTEST-1435226439255', 
            'skinCode': 'X7hsNDWp'
        }

        result = signer.sign(fields)

        assert 'merchantSig' in result
        assert result['merchantSig'] == (
            'GJ1asjR5VmkvihDJxCd8yE2DGYOKwWwJCBiV3R51NFg=')

    def test_verify(self):
        secret_key = (
            '4468D9782DEF54FCD706C9100C71EC43932B1EBC2ACF6BA0560C05AAA7550C48')
        signer = HMACSha256(secret_key)
        fields = {
            'authResult': 'AUTHORISED',
            'merchantReference': 'SKINTEST-test',
            'merchantReturnData' : 'YourMerchantReturnData',
            'paymentMethod' : 'visa',
            'pspReference' : '7914447419663319',
            'shopperLocale' : 'en_GB',
            'skinCode' : '314lwMhy',
            'merchantSig': 'H8hU6s0b12EOAQo0hAZHno8tc7DhIv4r1WF/jjLZUqE='
        }

        assert signer.verify(fields)

    def test_compute_hash(self):
        """Make sure the compute_hash method works as expected.

        We are using the same "fields" as in ``test_verify``, which is itself
        taken from the Adyen documentation.

        This should be safe enough!
        """
        secret_key = (
            '4468D9782DEF54FCD706C9100C71EC43932B1EBC2ACF6BA0560C05AAA7550C48')
        signer = HMACSha256(secret_key)

        adyen_sample = (
            'authResult:'
            'merchantReference:'
            'merchantReturnData:'
            'paymentMethod:'
            'pspReference:'
            'shopperLocale:'
            'skinCode:'
            'AUTHORISED:'
            'SKINTEST-test:'
            'YourMerchantReturnData:'
            'visa:'
            '7914447419663319:'
            'en_GB:'
            '314lwMhy')
        exepected_signature = 'H8hU6s0b12EOAQo0hAZHno8tc7DhIv4r1WF/jjLZUqE='
 
        assert signer.compute_hash(adyen_sample) == exepected_signature
