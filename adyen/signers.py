"""Signers are helpers to sign and verify Adyen requests & responses.

There are currently 2 type of signatures:

* SHA-1, deprecated by Adyen but still used,
* SHA-2 (256), preferred by Adyen.

Each signer follows different rules to sign payment request form, and to verify
Adyen return response and Adyen notification.

.. note::

    **About the signature:**

    The data passed, in the form fields, is concatenated into a string,
    referred to as the “signing string”. The HMAC signature is then computed
    over using a key that is specified in the Adyen Skin settings (stored
    into the :attr:`AbstractSigner.secret key`).

    The signature is passed along with the form data and once Adyen receives it
    they use the key to verify that the data has not been tampered with in
    transit.

    The signing string should be packed into a binary format containing hex
    characters, and then base64-encoded for transmission.

"""
import base64
import hashlib
import hmac

from adyen.constants import Constants


class AbstractSigner:
    """Abstract base class that define the common interface.

    A signer must expose three methods:

    * :meth:`sign`: take form fields and return a dict of signature fields.
    * :meth:`verify`: take a dict of fields and make sure there have an
        appropriate signature field.
    * :meth:`compute_hash`: take a signature string and compute its hash value.

    These methods are not implementd by the :class:`AbstractSigner`, therefore
    subclasses **must** implement them.
    """
    def __init__(self, secret_key):
        self.secret_key = secret_key
        """Adyen Skin secret key

        This secret key is used to sign payment request, and verify payment
        return response and payment notification.
        """

    def sign(self, fields):
        """Sign the given form ``fields`` and return the signature fields.

        :param dict fields: The form fields used to perform a payment request
        :return: A dict of signature fields
        :rtype: ``dict``

        A payment request form must contains specific signature fields,
        depending on the selected sign method.
        """
        raise NotImplementedError

    def verify(self, fields):
        """Verify ``fields`` contains the appropriate signatures.

        :param dict fields: A dict of fields, given by a payment return
            response or by a payment notification.
        :return: ``True`` the ``fields`` contain valid signatures
        :rtype: ``boolean``

        Adyen can secure communication with merchant site using signatures:

        * ``merchantSig`` for the return URL,
        * ``additionalData.hmacSignature`` for notification,

        And this method can be used for both, provided with all the fields
        as a flat ``dict``.

        The following example is taken from the Adyen documentation::

            {
               "live":"false",
               "notificationItems": [
                  {
                     "notificationRequestItem": {
                        "additionalData": {
                           "hmacSignature":"SIGN_KEY"
                        },
                        "amount": {
                           "value":1130,
                           "currency":"EUR"
                        },
                        "pspReference":"7914073381342284",
                        # ... other fields
                     }
                  }
               ]
            }

        The expected fields will be::

            {
                'additionalData.hmacSignature': 'SIGN_KEY',
                'amount.value': 1130,
                'amount.currency': 'EUR',
                'pspReference: "7914073381342284"
                # ... other fields
            }

        This format correspond to the ``POST`` notification format.
        """
        raise NotImplementedError

    def compute_hash(self, signature):
        """Return a hash for the given ``signature`` string.

        :param str signature: A ``signature`` used to compute hash.
        :return: A hashed version of the ``signature`` using the
            :attr:`secret_key` and the defined hash algorithm.

        Each implementation should simply use a different hash algorithm to
        sign the ``signature`` string. This method is not supposed to know how
        the ``signature`` string is built.
        """
        raise NotImplementedError


class HMACSha1(AbstractSigner):
    """Implement a HMAC signature with SHA-1 algorithm.

    .. seealso::

        The Adyen documentation about `SHA-1 deprecated method`__ for a general
        explanation. The delivery, billing and shopper signatures are
        explained in the `Open Invoice`__ documentation.

        .. __: https://docs.adyen.com/manuals/hpp-manual#hmacpaymentsetupsha1deprecated
        .. __: https://docs.adyen.com/manuals/open-invoice-manual#openinvoiceprocess

    """
    PAYMENT_FORM_HASH_KEYS = (
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
    """List of fields to sign payment request form.

    This is used to build the ``merchantSig`` signature. Note that the order of
    the fields matter to compute the hash with the SHA-1 algorithm.
    """

    PAYMENT_DELIVERY_HASH_KEYS = (
        Constants.DELIVERY_STREET,
        Constants.DELIVERY_NUMBER,
        Constants.DELIVERY_CITY,
        Constants.DELIVERY_POSTCODE,
        Constants.DELIVERY_STATE,
        Constants.DELIVERY_COUNTRY,
    )
    """List of fields to sign delivery address in payment request form."""

    PAYMENT_BILLING_HASH_KEYS = (
        Constants.BILLING_STREET,
        Constants.BILLING_NUMBER,
        Constants.BILLING_CITY,
        Constants.BILLING_POSTCODE,
        Constants.BILLING_STATE,
        Constants.BILLING_COUNTRY,
    )
    """List of fields to sign billing address in payment request form."""

    PAYMENT_SHOPPER_HASH_KEYS = (
        Constants.SHOPPER_FIRSTNAME,
        Constants.SHOPPER_INFIX,
        Constants.SHOPPER_LASTNAME,
        Constants.SHOPPER_GENDER,
        Constants.SHOPPER_BIRTH_DAY,
        Constants.SHOPPER_BIRTH_MONTH,
        Constants.SHOPPER_BIRTH_YEAR,
        Constants.SHOPPER_PHONE,
    )
    """List of fields to sign shopper data in payment request form."""

    PAYMENT_RETURN_HASH_KEYS = (
        Constants.AUTH_RESULT,
        Constants.PSP_REFERENCE,
        Constants.MERCHANT_REFERENCE,
        Constants.SKIN_CODE,
        Constants.MERCHANT_RETURN_DATA,
    )
    """List of fields used verify payment result on return URL.

    These fields are given to tye payment return URL by Adyen. It is used to
    validate that the payment return URL has a valid ``merchantSig`` field.
    """

    def sign(self, fields):
        """Sign the given form ``fields`` and return the signature fields.

        .. seealso::

            The :meth:`AbstractSigner.sign` method for usage.

        """
        signature = ''.join(
            str(fields.get(key, '')) for key in self.PAYMENT_FORM_HASH_KEYS)

        sign_fields = {
            Constants.MERCHANT_SIG: self.compute_hash(signature)
        }

        if self.PAYMENT_DELIVERY_HASH_KEYS & fields.keys():
            # Add a delivery signature only if at least one key is provided.
            delivery_signature = ''.join(
                str(fields.get(key, ''))
                for key in self.PAYMENT_DELIVERY_HASH_KEYS)
            sign_fields[Constants.DELIVERY_SIG] = self.compute_hash(
                delivery_signature)

        if self.PAYMENT_BILLING_HASH_KEYS & fields.keys():
            # Add a billing signature only if at least one key is provided.
            delivery_signature = ''.join(
                str(fields.get(key, ''))
                for key in self.PAYMENT_BILLING_HASH_KEYS)
            sign_fields[Constants.BILLING_SIG] = self.compute_hash(
                delivery_signature)

        if (self.PAYMENT_SHOPPER_HASH_KEYS & fields.keys() or
            Constants.SHOPPER_TYPE in fields):
            # Add a shopper signature only if at least one key is provided or
            # if the shopper type is provided.
            shopper_signature = ''.join(
                str(fields.get(key, ''))
                for key in self.PAYMENT_SHOPPER_HASH_KEYS)
            sign_fields[Constants.SHOPPER_SIG] = self.compute_hash(
                shopper_signature)

        return sign_fields

    def verify(self, fields):
        """Verify ``fields`` contains the appropriate signatures.

        .. warning::

            This version validate only the ``merchantSig`` signature, given to
            the payment return URL. Other signature fields are ignored (in
            particular for notification signature).

        .. seealso::

            The :meth:`AbstractSigner.verify` method for usage.

        """
        if Constants.MERCHANT_SIG in fields:
            given_hash = fields[Constants.MERCHANT_SIG]
            signature = ''.join(
                str(fields.get(key, ''))
                for key in self.PAYMENT_RETURN_HASH_KEYS)
            return given_hash == self.compute_hash(signature)

        return True

    def compute_hash(self, signature):
        """Compute hash using the ``hashlib.sha1`` algorithm.

        .. seealso::

            The :meth:`AbstractSigner.compute_hash` method for usage.

        """
        hm = hmac.new(self.secret_key.encode('utf-8'),
                      signature.encode('utf-8'),
                      hashlib.sha1)
        return base64.encodebytes(hm.digest()).strip().decode('utf-8')
