# -*- coding: utf-8 -*-

import base64
import hashlib
import hmac
import logging

from urllib.parse import parse_qs

logger = logging.getLogger('adyen')


# ---[ CONSTANTS ]---

class Constants:

    ADYEN = 'adyen'

    IDENTIFIER = 'identifier'
    SECRET_KEY = 'secret_key'
    ACTION_URL = 'action_url'

    MERCHANT_ACCOUNT = 'merchantAccount'
    MERCHANT_REFERENCE = 'merchantReference'
    MERCHANT_RETURN_URL = 'resURL'
    MERCHANT_RETURN_DATA = 'merchantReturnData'
    MERCHANT_SIG = 'merchantSig'

    SHOPPER_EMAIL = 'shopperEmail'
    SHOPPER_LOCALE = 'shopperLocale'
    SHOPPER_REFERENCE = 'shopperReference'
    SHOPPER_STATEMENT = 'shopperStatement'
    SHOPPER_TYPE = 'shopperType'

    COUNTRY_CODE = 'countryCode'
    CURRENCY_CODE = 'currencyCode'
    PAYMENT_AMOUNT = 'paymentAmount'

    SKIN_CODE = 'skinCode'
    SHIP_BEFORE_DATE = 'shipBeforeDate'
    SESSION_VALIDITY = 'sessionValidity'

    PAYMENT_METHOD = 'paymentMethod'
    ALLOWED_METHODS = 'allowedMethods'
    BLOCKED_METHODS = 'blockedMethods'
    RECURRING_CONTRACT = 'recurringContract'
    BILLING_ADDRESS_TYPE = 'billingAddressType'
    DELIVERY_ADDRESS_TYPE = 'deliveryAddressType'
    OFFSET = 'offset'

    PSP_REFERENCE = 'pspReference'
    AUTH_RESULT = 'authResult'

    PAYMENT_RESULT_AUTHORISED = 'AUTHORISED'
    PAYMENT_RESULT_REFUSED = 'REFUSED'
    PAYMENT_RESULT_CANCELLED = 'CANCELLED'
    PAYMENT_RESULT_PENDING = 'PENDING'
    PAYMENT_RESULT_ERROR = 'ERROR'


# ---[ EXCEPTIONS ]---

class MissingParameterException(ValueError):
    pass


class MissingFieldException(ValueError):
    pass


class UnexpectedFieldException(ValueError):
    pass


class InvalidTransactionException(ValueError):
    pass


# ---[ GATEWAY ]---

class Gateway:

    MANDATORY_SETTINGS = (
        Constants.IDENTIFIER,
        Constants.SECRET_KEY,
        Constants.ACTION_URL,
    )

    def __init__(self, settings={}):
        """
        Initialize an Adyen gateway.
        """

        self.identifier = settings.get(Constants.IDENTIFIER)
        self.secret_key = settings.get(Constants.SECRET_KEY)
        self.action_url = settings.get(Constants.ACTION_URL)

        if self.identifier is None or self.secret_key is None or self.action_url is None:
            raise MissingParameterException(
                "You need to specify the following parameters to initialize "
                "the Adyen gateway: identifier, secret_key, action_url. "
                "Please check your configuration."
            )

    def _compute_hash(self, keys, params):
        """
        Compute a validation hash for Adyen transactions.

        General method:

        The signature is computed using the HMAC algorithm with the SHA-1
        hashing function. The data passed, in the form fields, is concatenated
        into a string, referred to as the “signing string”. The HMAC signature
        is then computed over using a key that is specified in the Adyen Skin
        settings. The signature is passed along with the form data and once
        Adyen receives it, they use the key to verify that the data has not
        been tampered with in transit. The signing string should be packed
        into a binary format containing hex characters, and then base64-encoded
        for transmission.

        Payment Setup:

        When setting up a payment the signing string is as follows:

        paymentAmount + currencyCode + shipBeforeDate + merchantReference
        + skinCode + merchantAccount + sessionValidity + shopperEmail
        + shopperReference + recurringContract + allowedMethods
        + blockedMethods + shopperStatement + merchantReturnData
        + billingAddressType + deliveryAddressType + shopperType + offset

        The order of the fields must be exactly as described above.
        If you are not using one of the fields, such as allowedMethods,
        the value for this field in the signing string is an empty string.

        Payment Result:

        The payment result uses the following signature string:

        authResult + pspReference + merchantReference + skinCode
        + merchantReturnData
        """
        signature = ''.join(str(params.get(key, '')) for key in keys)
        hm = hmac.new(self.secret_key.encode(), signature.encode(), hashlib.sha1)
        hash_ = base64.encodebytes(hm.digest()).strip().decode('utf-8')
        return hash_

    def _build_form_fields(self, adyen_request):
        """
        Return the hidden fields of an HTML form
        allowing to perform this request.
        """
        return adyen_request.build_form_fields()

    def build_payment_form_fields(self, params):
        return self._build_form_fields(PaymentFormRequest(self, params))

    def _process_response(self, adyen_response, query_string):
        """
        Process an Adyen response.
        """
        return adyen_response.process()

    def process_payment_response(self, query_string):
        return self._process_response(PaymentResponse(self, query_string))


class BaseInteraction:

    def check_fields(self):
        """
        Validate required and optional fields for both
        requests and responses.
        """

        params = self.params

        # Check that all mandatory fields are present.
        for field_name in self.REQUIRED_FIELDS:
            if not params.get(field_name):
                raise MissingFieldException(
                    "The %s field is missing" % field_name
                )

        # Check that no unexpected field is present.
        expected_fields = self.REQUIRED_FIELDS + self.OPTIONAL_FIELDS
        for field_name in params.keys():
            if field_name not in expected_fields:
                raise UnexpectedFieldException(
                    "The %s field is unexpected" % field_name
                )


# ---[ REQUESTS ]---

class BaseRequest(BaseInteraction):
    REQUIRED_FIELDS = ()
    OPTIONAL_FIELDS = ()
    HASH_KEYS = ()

    def __init__(self, client, params={}):
        self.client = client
        self.params = params
        self.validate()

        # Compute request hash.
        self.params.update({Constants.MERCHANT_SIG: self.hash()})

    def validate(self):
        self.check_fields()

    def hash(self):
        return self.client._compute_hash(self.HASH_KEYS, self.params)


# ---[ FORM-BASED REQUESTS ]---

class FormRequest(BaseRequest):
    def build_form_fields(self):
        return [{'type': 'hidden', 'name': name, 'value': value}
            for name, value in self.params.items()]


class PaymentFormRequest(FormRequest):
    REQUIRED_FIELDS = (
        Constants.MERCHANT_ACCOUNT,
        Constants.MERCHANT_REFERENCE,
        Constants.SHOPPER_REFERENCE,
        Constants.SHOPPER_EMAIL,
        Constants.CURRENCY_CODE,
        Constants.PAYMENT_AMOUNT,
        Constants.SESSION_VALIDITY,
        Constants.SHIP_BEFORE_DATE,
    )
    OPTIONAL_FIELDS = (
        Constants.MERCHANT_SIG,
        Constants.SKIN_CODE,
        Constants.RECURRING_CONTRACT,
        Constants.ALLOWED_METHODS,
        Constants.BLOCKED_METHODS,
        Constants.SHOPPER_STATEMENT,
        Constants.SHOPPER_LOCALE,
        Constants.COUNTRY_CODE,
        Constants.MERCHANT_RETURN_URL,
        Constants.MERCHANT_RETURN_DATA,
        Constants.BILLING_ADDRESS_TYPE,
        Constants.DELIVERY_ADDRESS_TYPE,
        Constants.SHOPPER_TYPE,
        Constants.OFFSET,
    )

    # Note that the order of the keys matter to compute the hash!
    HASH_KEYS = (
        Constants.PAYMENT_AMOUNT,
        Constants.CURRENCY_CODE,
        Constants.SHIP_BEFORE_DATE,
        Constants.MERCHANT_REFERENCE,
        Constants.SKIN_CODE,
        Constants.MERCHANT_ACCOUNT,
        Constants.SESSION_VALIDITY,
        Constants.SHOPPER_EMAIL,
        Constants.SHOPPER_REFERENCE,
        Constants.RECURRING_CONTRACT,
        Constants.ALLOWED_METHODS,
        Constants.BLOCKED_METHODS,
        Constants.SHOPPER_STATEMENT,
        Constants.MERCHANT_RETURN_DATA,
        Constants.BILLING_ADDRESS_TYPE,
        Constants.DELIVERY_ADDRESS_TYPE,
        Constants.SHOPPER_TYPE,
        Constants.OFFSET
    )


# ---[ RESPONSES ]---

class BaseResponse(BaseInteraction):
    REQUIRED_FIELDS = ()
    OPTIONAL_FIELDS = ()
    HASH_KEYS = ()

    def __init__(self, client, query_string):
        self.client = client
        self.secret_key = client.secret_key
        self.params = parse_qs(query_string, keep_blank_values=True)
        self.params = {key: value[0] for (key, value) in self.params.items()}

    def validate(self):

        self.check_fields()

        # Check that the transaction has not been tampered with.
        received_hash = self.params.pop(Constants.MERCHANT_SIG)
        expected_hash = self.hash()
        if expected_hash != received_hash:
            raise InvalidTransactionException(
                "The transaction is invalid. "
                "This may indicate a fraud attempt."
            )

    def hash(self):
        return self.client._compute_hash(self.HASH_KEYS, self.params)

    def process(self):
        payment_result = self.params.get(Constants.AUTH_RESULT, None)
        accepted = payment_result == Constants.PAYMENT_RESULT_AUTHORISED
        return accepted, self.params


class PaymentResponse(BaseResponse):
    REQUIRED_FIELDS = (
        Constants.AUTH_RESULT,
        Constants.MERCHANT_REFERENCE,
        Constants.MERCHANT_SIG,
        Constants.PAYMENT_METHOD,
        Constants.PSP_REFERENCE,
        Constants.SHOPPER_LOCALE,
        Constants.SKIN_CODE,
    )
    OPTIONAL_FIELDS = (
        Constants.MERCHANT_RETURN_DATA,
    )

    # Note that the order of the keys matter to compute the hash!
    HASH_KEYS = (
        Constants.AUTH_RESULT,
        Constants.PSP_REFERENCE,
        Constants.MERCHANT_REFERENCE,
        Constants.SKIN_CODE,
        Constants.MERCHANT_RETURN_DATA,
    )
