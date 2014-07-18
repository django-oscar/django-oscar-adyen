# -*- coding: utf-8 -*-

import hashlib
import logging
import requests

from urllib.parse import parse_qs

logger = logging.getLogger('adyen')


# ---[ CONSTANTS ]---

class Constants:
    pass


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

class Gateway():

    MANDATORY_SETTINGS = (
        Constants.IDENTIFIER,
        Constants.PASSWORD,
        Constants.PRIMARY_URL,
        Constants.SECONDARY_URL,
    )

    def __init__(self, settings={}):
        """ Initialize an Adyen gateway. """

        self.identifier = settings.get('identifier', None)
        self.password = settings.get('password', None)
        self.action_url = settings.get('primary_url', None)

        if self.identifier is None or self.password is None or self.action_url is None:

            raise MissingParameterException(
                "You need to specify the following parameters to initialize "
                "the Adyen gateway: identifier, password, action_url. "
                "Please check your configuration."
            )

    def _compute_hash(self, params_dict):
        password = self.password
        parameters = sorted([
            '%s=%s' % (key, value) for key, value in params_dict.items()
        ])
        clear_str = password + password.join(parameters) + password
        return hashlib.sha256(clear_str.encode('utf-8')).hexdigest()

    def _build_form_fields(self, adyen_request, create_alias=False):
        """ Return the hidden fields of an HTML form
        allowing to perform this request. """
        return adyen_request.build_form_fields(create_alias)

    def build_payment_form_fields(self, params, create_alias=False):
        params.update({
            Constants.OPERATIONTYPE: Constants.OPERATIONTYPE_PAYMENT,
        })
        return self._build_form_fields(
            PaymentFormRequest(self, params), create_alias
        )

    def _send_request(self, adyen_request, create_alias=False):
        """ Perform an Adyen request directly. """
        return adyen_request.send(create_alias)

    def send_payment_request(self, params, create_alias=False):
        params.update({
            Constants.OPERATIONTYPE: Constants.OPERATIONTYPE_PAYMENT,
        })
        return self._send_request(
            PaymentDirectRequest(self, params), create_alias
        )

    def _process_response(self, adyen_response, query_string):
        """ Process an Adyen response. """
        return adyen_response.process()

    def process_payment_response(self, query_string):
        return self._process_response(
            PaymentResponse(self, query_string)
        )


# ---[ REQUESTS ]---

class BaseRequest(object):
    REQUIRED_FIELDS = ()
    OPTIONAL_FIELDS = ()

    def __init__(self, client, params={}):
        self.client = client
        self.params = {
            Constants.IDENTIFIER: self.client.identifier,
            Constants.VERSION: Constants.API_VERSION,
        }
        self.params.update(params)
        self._validate()

        # compute request hash
        self.params.update({Constants.HASH: self._hash()})

    def _validate(self):

        # check that all mandatory fields are present
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in self.params:
                raise MissingFieldException(
                    "The %s field is missing" % field_name
                )

        # check that no unexpected field has been passed
        expected_fields = self.REQUIRED_FIELDS + self.OPTIONAL_FIELDS
        for field_name in self.params.keys():
            if field_name not in expected_fields:
                raise UnexpectedFieldException(
                    "The %s field is unexpected" % field_name
                )

    def _hash(self):
        return self.client._compute_hash(self.params)


# ---[ FORM-BASED REQUESTS ]---

class FormRequest(BaseRequest):

    def build_form_fields(self, create_alias=False):
        if create_alias:
            self.params.update({
                Constants.CREATEALIAS: Constants.YES,
            })
        return [{'type': 'hidden', 'name': name, 'value': value}
            for name, value in self.params.items()]

"""
<input type="hidden" name="merchantReference" value="Internet Order 12345" />                       = ORDER ID
<input type="hidden" name="paymentAmount" value="100" />                                            = AMOUNT IN CENTS
<input type="hidden" name="currencyCode" value="EUR" />                                             = CURRENCY CODE
<input type="hidden" name="shipBeforeDate" value="2013-12-03" />                                    ---> mandatory, strangely enough
<input type="hidden" name="skinCode" value="TOuEXu2m" />                                            ---> only if multiple skins exist (not our case?)
<input type="hidden" name="merchantAccount" value="SupportAdyenDemo" />                             = ADYEN IDENTIFIER
<input type="hidden" name="countryCode" value="be" />                                               = COUNTRY
<input type="hidden" name="shopperLocale" value="be_NL" />                                          = LOCALE
<input type="hidden" name="sessionValidity" value="2014-09-23T12:09:39Z" />                         --> at what time must the payment have been made
<input type="hidden" name="merchantSig" value="3iWDU/V5RMtdaiZC4YRIpoX9/v0=" />                     = VALIDATION HASH
<input type="hidden" name="shopperEmail" value="test102@gmail.com" />                               = CUSTOMER EMAIL
<input type="hidden" name="shopperReference" value="test102@gmail.com" />                           = CUSTOMER ID
"""

class PaymentFormRequest(FormRequest):
    REQUIRED_FIELDS = (
        Constants.IDENTIFIER, Constants.OPERATIONTYPE,
        Constants.CLIENTIDENT, Constants.DESCRIPTION,
        Constants.ORDERID, Constants.VERSION,
        Constants.AMOUNT,
    )
    OPTIONAL_FIELDS = (
        Constants.CARDTYPE, Constants.CLIENTEMAIL,
        Constants.CARDFULLNAME, Constants.LANGUAGE,
        Constants.EXTRADATA, Constants.CLIENTDOB,
        Constants.CLIENTADDRESS, Constants.CREATEALIAS,
        Constants._3DSECURE, Constants._3DSECUREDISPLAYMODE,
        Constants.USETEMPLATE, Constants.HIDECLIENTEMAIL,
        Constants.HIDECARDFULLNAME,
    )


# ---[ RESPONSES ]---

class BaseResponse(object):
    REQUIRED_FIELDS = ()

    def __init__(self, client, query_string):
        self.client = client
        self.password = client.password
        self.query = parse_qs(query_string, keep_blank_values=True)
        self.query = {key: value[0] for (key, value) in self.query.items()}

    def validate(self):

        # check that all mandatory fields are present
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in self.query:
                raise MissingFieldException(
                    "The %s field is missing" % field_name
                )

        # check that the transaction has not been tampered with
        received_hash = self.query.pop(Constants.HASH)
        expected_hash = self.client._compute_hash(self.query)
        if expected_hash != received_hash:
            raise InvalidTransactionException(
                "The transaction is invalid. "
                "This may indicate a fraud attempt."
            )

    def process(self):
        exec_code = self.query.get(Constants.EXECCODE, '')
        accepted = exec_code == Constants.EXECCODE_ACCEPTED
        return accepted, self.query


class PaymentResponse(BaseResponse):
    REQUIRED_FIELDS = (
        Constants.CARDCOUNTRY,
        Constants.OPERATIONTYPE,
        Constants._3DSECURE,
        Constants.EXTRADATA,
        Constants.EXECCODE,
        Constants.LANGUAGE,
        Constants.CARDCODE,
        Constants.HASH,
        Constants.CURRENCY,
        Constants.CLIENTIDENT,
        Constants.ALIAS,
        Constants.ORDERID,
        Constants.CLIENTEMAIL,
        Constants.VERSION,
        Constants.TRANSACTIONID,
        Constants.AMOUNT,
        Constants.DESCRIPTOR,
        Constants.IDENTIFIER,
        Constants.MESSAGE,
    )
