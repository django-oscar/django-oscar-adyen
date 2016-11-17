

class Constants:
    """List of all constants."""
    ACCEPTED_NOTIFICATION = '[accepted]'

    ACTION_URL = 'action_url'
    ADYEN = 'adyen'
    ALLOWED_METHODS = 'allowedMethods'
    AUTH_RESULT = 'authResult'
    BLOCKED_METHODS = 'blockedMethods'
    COUNTRY_CODE = 'countryCode'
    CURRENCY = 'currency'
    CURRENCY_CODE = 'currencyCode'

    EVENT_CODE = 'eventCode'
    EVENT_CODE_AUTHORISATION = 'AUTHORISATION'
    EVENT_DATE = 'eventDate'

    FALSE = 'false'
    IDENTIFIER = 'identifier'
    SECRET_KEY = 'secret_key'
    SIGNER = 'signer'
    LIVE = 'live'

    PSP_REFERENCE = 'pspReference'
    TEST_REFERENCE_PREFIX = 'test_AUTHORISATION'
    REASON = 'reason'
    RECURRING_CONTRACT = 'recurringContract'
    SEPARATOR = ':'
    SESSION_VALIDITY = 'sessionValidity'
    SKIN_CODE = 'skinCode'
    SHIP_BEFORE_DATE = 'shipBeforeDate'
    ADDITIONAL_DATA_PREFIX = 'additionalData.'

    OFFSET = 'offset'
    OPERATIONS = 'operations'
    ORIGINAL_REFERENCE = 'originalReference'

    SUCCESS = 'success'
    TEST = 'test'
    TRUE = 'true'
    VALUE = 'value'

    # Payment related constants ---
    PAYMENT_BRAND_CODE = 'brandCode'
    PAYMENT_ISSUER_ID = 'issuerId'

    PAYMENT_AMOUNT = 'paymentAmount'
    PAYMENT_METHOD = 'paymentMethod'

    PAYMENT_RESULT_AUTHORISED = 'AUTHORISED'
    PAYMENT_RESULT_REFUSED = 'REFUSED'
    PAYMENT_RESULT_CANCELLED = 'CANCELLED'
    PAYMENT_RESULT_PENDING = 'PENDING'
    PAYMENT_RESULT_ERROR = 'ERROR'

    # Merchant related constants ---

    MERCHANT_SIG = 'merchantSig'

    MERCHANT_ACCOUNT = 'merchantAccount'
    MERCHANT_ACCOUNT_CODE = 'merchantAccountCode'
    MERCHANT_REFERENCE = 'merchantReference'
    MERCHANT_RETURN_DATA = 'merchantReturnData'
    MERCHANT_RETURN_URL = 'resURL'

    # Delivery address related constants ---

    DELIVERY_SIG = 'deliveryAddressSig'
    DELIVERY_ADDRESS_TYPE = 'deliveryAddressType'

    DELIVERY_STREET = 'deliveryAddress.street'
    DELIVERY_NUMBER = 'deliveryAddress.houseNumberOrName'
    DELIVERY_CITY = 'deliveryAddress.city'
    DELIVERY_POSTCODE = 'deliveryAddress.postalCode'
    DELIVERY_STATE = 'deliveryAddress.stateOrProvince'
    DELIVERY_COUNTRY = 'deliveryAddress.country'

    # Billing address related constants ---

    BILLING_SIG = 'billingAddressSig'
    BILLING_ADDRESS_TYPE = 'billingAddressType'

    BILLING_STREET = 'billingAddress.street'
    BILLING_NUMBER = 'billingAddress.houseNumberOrName'
    BILLING_CITY = 'billingAddress.city'
    BILLING_POSTCODE = 'billingAddress.postalCode'
    BILLING_STATE = 'billingAddress.stateOrProvince'
    BILLING_COUNTRY = 'billingAddress.country'

    # Shopper related constants ---

    SHOPPER_EMAIL = 'shopperEmail'
    SHOPPER_LOCALE = 'shopperLocale'
    SHOPPER_REFERENCE = 'shopperReference'
    SHOPPER_STATEMENT = 'shopperStatement'

    SHOPPER_SIG = 'shopperSig'
    SHOPPER_TYPE = 'shopperType'

    SHOPPER_FIRSTNAME = 'shopper.firstName'
    SHOPPER_INFIX = 'shopper.infix'
    SHOPPER_LASTNAME = 'shopper.lastName'
    SHOPPER_GENDER = 'shopper.gender'
    SHOPPER_BIRTH_DAY = 'shopper.dateOfBirthDayOfMonth'
    SHOPPER_BIRTH_MONTH = 'shopper.dateOfBirthMonth'
    SHOPPER_BIRTH_YEAR = 'shopper.dateOfBirthYear'
    SHOPPER_PHONE = 'shopper.telephoneNumber'

    INVOICE_NUMLINES = 'openinvoicedata.numberOfLines'
    INVOICE_SIG = 'openinvoicedata.sig'
    INVOICE_LINE_CURRENCY = 'openinvoicedata.line%d.currencyCode'
    INVOICE_LINE_DESCRIPTION = 'openinvoicedata.line%d.description'
    INVOICE_LINE_ITEMAMOUNT = 'openinvoicedata.line%d.itemAmount'
    INVOICE_LINE_ITEMVATAMOUNT = 'openinvoicedata.line%d.itemVatAmount'
    INVOICE_LINE_ITEMVATPERCENTAGE = 'openinvoicedata.line%d.itemVatPercentage'
    INVOICE_LINE_LINEREFERENCE = 'openinvoicedata.line%d.lineReference'
    INVOICE_LINE_NUMBEROFITEMS = 'openinvoicedata.line%d.numberOfItems'
    INVOICE_LINE_VATCATEGORY = 'openinvoicedata.line%d.vatCategory'
