# -*- coding: utf-8 -*-

import base64
import binascii
import hashlib
import hmac
import logging

logger = logging.getLogger('adyen')


# ---[ CONSTANTS ]---

class Constants:

    ACCEPTED_NOTIFICATION = '[accepted]'

    ACTION_URL = 'action_url'
    ADYEN = 'adyen'
    ALLOWED_METHODS = 'allowedMethods'
    AUTH_RESULT = 'authResult'
    BILLING_ADDRESS_TYPE = 'billingAddressType'
    BLOCKED_METHODS = 'blockedMethods'
    COUNTRY_CODE = 'countryCode'
    CURRENCY = 'currency'
    CURRENCY_CODE = 'currencyCode'
    DELIVERY_ADDRESS_TYPE = 'deliveryAddressType'

    EVENT_CODE = 'eventCode'
    EVENT_CODE_AUTHORISATION = 'AUTHORISATION'
    EVENT_DATE = 'eventDate'

    FALSE = 'false'
    HMAC_ALGORITHM = 'hmacAlgorithm'
    IDENTIFIER = 'identifier'
    LIVE = 'live'

    MERCHANT_ACCOUNT = 'merchantAccount'
    MERCHANT_ACCOUNT_CODE = 'merchantAccountCode'
    MERCHANT_REFERENCE = 'merchantReference'
    MERCHANT_RETURN_DATA = 'merchantReturnData'
    MERCHANT_RETURN_URL = 'resURL'
    MERCHANT_SIG = 'merchantSig'

    OFFSET = 'offset'
    OPERATIONS = 'operations'
    ORIGINAL_REFERENCE = 'originalReference'

    PAYMENT_AMOUNT = 'paymentAmount'
    PAYMENT_METHOD = 'paymentMethod'
    PAYMENT_RESULT_AUTHORISED = 'AUTHORISED'
    PAYMENT_RESULT_REFUSED = 'REFUSED'
    PAYMENT_RESULT_CANCELLED = 'CANCELLED'
    PAYMENT_RESULT_PENDING = 'PENDING'
    PAYMENT_RESULT_ERROR = 'ERROR'

    PSP_REFERENCE = 'pspReference'
    TEST_REFERENCE_PREFIX = 'test_AUTHORISATION'
    REASON = 'reason'
    RECURRING_CONTRACT = 'recurringContract'
    SECRET_KEY = 'secret_key'
    SEPARATOR = ':'
    SESSION_VALIDITY = 'sessionValidity'
    SKIN_CODE = 'skinCode'
    SHIP_BEFORE_DATE = 'shipBeforeDate'
    ADDITIONAL_DATA_PREFIX = 'additionalData.'

    SHOPPER_EMAIL = 'shopperEmail'
    SHOPPER_LOCALE = 'shopperLocale'
    SHOPPER_REFERENCE = 'shopperReference'
    SHOPPER_STATEMENT = 'shopperStatement'
    SHOPPER_TYPE = 'shopperType'

    SUCCESS = 'success'
    TEST = 'test'
    TRUE = 'true'
    VALUE = 'value'


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
        Constants.HMAC_ALGORITHM,
    )

    def __init__(self, request, settings=None):
        """
        Initialize an Adyen gateway.
        """
        if settings is None:
            settings = {}

        if not all([x in settings.keys() for x in self.MANDATORY_SETTINGS]):
            raise MissingParameterException(
                "You need to specify the following parameters to initialize "
                "the Adyen gateway: %s. Please check your configuration." %
                ", ".join(self.MANDATORY_SETTINGS)
            )

        self.identifier = settings.get(Constants.IDENTIFIER)
        self.secret_key = settings.get(Constants.SECRET_KEY)
        self.action_url = settings.get(Constants.ACTION_URL)
        self.hmac_algorithm = settings.get(Constants.HMAC_ALGORITHM)

        if request:
            # We must first find out whether this is a redirection or a notification.
            self.request = request
            if request.method == 'GET':
                self.response_class = globals()['PaymentRedirection%s' % self.hmac_algorithm]
            elif request.method == 'POST':
                self.response_class = globals()['PaymentNotification%s' % self.hmac_algorithm]
            else:
                raise RuntimeError("Only GET and POST requests are supported.")
        else:
            self.request = None

    def _compute_hash(self, signature):
        """
        Compute a validation hash for Adyen transactions.

        General method:

        The signature is computed using the HMAC algorithm with a hashing function.
        Adyen currenly supports SHA1 (deprecated) and SHA256 hashing. The default
        hashing function is SHA1 for backward compatibility, but can be set using
        the configuration system, e.g. by setting ADYEN_HMAC_ALGORITHM to 'SHA256'
        in the Django settings when using settings-based configuration.

        The data passed, in the form fields, is concatenated into a string, referred
        to as the “signing string”. The HMAC signature is then computed over using a
        key that is specified in the Adyen Skin settings. The signature is passed along
        with the form data and once Adyen receives it, they use the key to verify that
        the data has not been tampered with in transit. The signing string should be
        packed into a binary format containing hex characters, and then base64-encoded
        for transmission.

        The actual fields used for generating the both the signing string and the
        hash are configured in the appropriate response classes. e.g.
        `PaymentFormRequest`, `PaymentRedirectionSHA1` or `PaymentRedirectionSHA256`.
        """
        hmac_ = getattr(self, '_get_%s_hmac' % self.hmac_algorithm.lower())(signature)
        hash_ = base64.b64encode(hmac_.digest())
        return hash_.strip().decode('utf-8')

    def _get_sha1_hmac(self, signature):
        return hmac.new(self.secret_key.encode(), signature.encode(), hashlib.sha1)

    def _get_sha256_hmac(self, signature):
        hmac_key = binascii.a2b_hex(self.secret_key)
        return hmac.new(hmac_key, signature.encode(), hashlib.sha256)

    def _build_form_fields(self, adyen_request):
        return adyen_request.build_form_fields()

    def build_payment_form_fields(self, params):
        """
        Return the hidden fields of an HTML form allowing to perform this request.
        """
        return self._build_form_fields(PaymentFormRequest(self, params))

    def _process_response(self, adyen_response, params):
        """
        Process an Adyen response.
        """
        return adyen_response.process()

    def get_response(self):
        """
        Retrieves an instance of a response class that can be used to process
        an Adyen response.

        :return: an instance of a response class.
        :rtype: BaseInteraction
        """
        if not self.request:
            raise RuntimeError("get_response can only be called in response to a request")

        # The constructor has already checked that the method is either POST or GET
        params = self.request.POST if self.request.method == 'POST' else self.request.GET
        return self.response_class(self, params)


class BaseInteraction:
    REQUIRED_FIELDS = ()
    OPTIONAL_FIELDS = ()
    HASH_KEYS = ()
    HASH_FIELD = None

    def _compute_signature(self, keys, params):
        """
        Generate a signature string to be used in hash calculations.

        :param keys: Keys to be used in the signature. Also keys to the params dictionary.
        :type keys: list
        :param params: Values for the signature.
        :type params: dict
        :return: A string representing the hashing signature.
        :rtype: str
        """
        return ''.join(str(params.get(key, '')) for key in keys)

    def hash(self):
        signature = self._compute_signature(self.HASH_KEYS, self.params)
        return self.client._compute_hash(signature)

    def validate(self):
        self.check_fields()

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


# ---[ FORM-BASED REQUESTS ]---

class PaymentFormRequest(BaseInteraction):
    """
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

        For more information, please see:
        https://docs.adyen.com/manuals/hpp-manual/hpp-hmac-calculation/hmac-payment-setup-sha-1-deprecated
    """
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
    HASH_FIELD = Constants.MERCHANT_SIG

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
        Constants.OFFSET,
    )

    def __init__(self, client, params=None):
        self.client = client
        self.params = params or {}
        self.validate()

        # Compute request hash.
        self.params.update({self.HASH_FIELD: self.hash()})

    def build_form_fields(self):
        return [{'type': 'hidden', 'name': name, 'value': value}
                for name, value in self.params.items()]


# ---[ RESPONSES ]---

class BaseResponse(BaseInteraction):

    def __init__(self, client, params):
        self.client = client
        self.secret_key = client.secret_key
        self.params = params

    def process(self):
        return NotImplemented


class BasePaymentNotification(BaseResponse):
    """
    Class used to process payment notifications (HTTPS POST from Adyen to our servers).

    Payment notifications can have multiple fields. They fall into four categories:
    - required: Must be included.
    - optional: Can be included.
    - additional data: Can be included. Format is 'additionalData.VALUE' and we don't need the
                       data at the moment, so it's ignored.
    - unexpected: We loudly complain.


    Subclasses for specific HMAC algorithms will need to define HASH_KEYS as appropriate.
    """
    REQUIRED_FIELDS = (
        Constants.CURRENCY,
        Constants.EVENT_CODE,
        Constants.EVENT_DATE,
        Constants.LIVE,
        Constants.MERCHANT_ACCOUNT_CODE,
        Constants.MERCHANT_REFERENCE,
        Constants.PAYMENT_METHOD,
        Constants.PSP_REFERENCE,
        Constants.REASON,
        Constants.SUCCESS,
        Constants.VALUE,  # The payment amount may be retrieved here.
    )
    OPTIONAL_FIELDS = (
        Constants.OPERATIONS,
        Constants.ORIGINAL_REFERENCE,
    )

    def check_fields(self):
        """
        Delete unneeded additional data before validating.

        Adyen's payment notification can come with additional data.
        It can mostly be turned on and off in the notifications settings,
        but some bits always seem to be delivered with the new
        "System communication" setup (instead of the old "notifications" tab
        in the settings).
        We currently don't need any of that data, so we just drop it
        before validating the notification.
        :return:
        """
        self.params = {
            key: self.params[key]
            for key in self.params if Constants.ADDITIONAL_DATA_PREFIX not in key
        }
        super().check_fields()

    def process(self):
        payment_result = self.params.get(Constants.SUCCESS, None)
        accepted = payment_result == Constants.TRUE
        status = (Constants.PAYMENT_RESULT_AUTHORISED if accepted
                  else Constants.PAYMENT_RESULT_REFUSED)
        return accepted, status, self.params


class PaymentNotificationSHA1(BasePaymentNotification):
    pass


class PaymentNotificationSHA256(BasePaymentNotification):
    HASH_KEYS = (
        Constants.PSP_REFERENCE,
        Constants.ORIGINAL_REFERENCE,
        Constants.MERCHANT_ACCOUNT_CODE,
        Constants.MERCHANT_REFERENCE,
        Constants.VALUE,
        Constants.CURRENCY,
        Constants.EVENT_CODE,
        Constants.SUCCESS
    )


class BasePaymentRedirection(BaseResponse):
    """
    Class used to process payment notifications from the user; when they paid on Adyen
    and get redirected back to our site. HTTP GET from user's browser.

    Subclasses for specific HMAC algorithms will need to define HASH_KEYS as appropriate.
    """
    REQUIRED_FIELDS = (
        Constants.AUTH_RESULT,
        Constants.MERCHANT_REFERENCE,
        Constants.MERCHANT_SIG,
        Constants.SHOPPER_LOCALE,
        Constants.SKIN_CODE,
    )
    OPTIONAL_FIELDS = (
        Constants.MERCHANT_RETURN_DATA,  # The payment amount may be retrieved here.
        Constants.PAYMENT_METHOD,
        Constants.PSP_REFERENCE,
    )
    HASH_FIELD = Constants.MERCHANT_SIG

    def validate(self):
        super().validate()

        # Check that the transaction has not been tampered with.
        received_hash = self.params.get(self.HASH_FIELD)
        expected_hash = self.hash()
        if not received_hash or expected_hash != received_hash:
            raise InvalidTransactionException(
                "The transaction is invalid. This may indicate a fraud attempt.")

    def process(self):
        payment_result = self.params[Constants.AUTH_RESULT]
        accepted = payment_result == Constants.PAYMENT_RESULT_AUTHORISED
        return accepted, payment_result, self.params


class PaymentRedirectionSHA1(BasePaymentRedirection):
    """
        Payment Result:

        The payment result uses the following signature string:

        authResult + pspReference + merchantReference + skinCode
        + merchantReturnData
    """
    # Note that the order of the keys matter to compute the hash!
    HASH_KEYS = (
        Constants.AUTH_RESULT,
        Constants.PSP_REFERENCE,
        Constants.MERCHANT_REFERENCE,
        Constants.SKIN_CODE,
        Constants.MERCHANT_RETURN_DATA,
    )


class PaymentRedirectionSHA256(BasePaymentRedirection):
    """
    Hashing keys taken from:
    https://docs.adyen.com/display/TD/Payment+Response+merchantSig+-+SHA+256
    """
    # Note that the order of the keys matter to compute the hash!
    HASH_KEYS = (
        Constants.AUTH_RESULT,
        Constants.MERCHANT_REFERENCE,
        Constants.MERCHANT_RETURN_DATA,
        Constants.PAYMENT_METHOD,
        Constants.PSP_REFERENCE,
        Constants.SHOPPER_LOCALE,
        Constants.SKIN_CODE,
    )

    def _compute_signature(self, keys, params):
        """
        Unlike the SHA1 signature, the SHA256 must also contain a prepended list of keys.
        """
        signature_params = list(keys) + [str(params.get(key, '')) for key in keys]
        return Constants.SEPARATOR.join(signature_params)
