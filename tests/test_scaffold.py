import datetime
import unittest

from oscar.apps.order.models import BillingAddress, ShippingAddress

from adyen.constants import Constants
from adyen.scaffold import Scaffold


class TestScaffold(unittest.TestCase):

    def test_get_fields_delivery(self):
        scaffold = Scaffold()

        address = ShippingAddress(
            first_name='First Name',
            last_name='Last Name',
            line1='First Line Address 1',
            line4='Bruxelles',
            postcode='1000',
            country_id='BE')

        order_data = {
            'shipping_address': address
        }
        fields = scaffold.get_fields_delivery(None, order_data)

        assert Constants.DELIVERY_STREET in fields
        assert Constants.DELIVERY_NUMBER in fields
        assert Constants.DELIVERY_CITY in fields
        assert Constants.DELIVERY_POSTCODE in fields
        assert Constants.DELIVERY_STATE in fields
        assert Constants.DELIVERY_COUNTRY in fields

        assert fields[Constants.DELIVERY_STREET] == 'First Line Address'
        assert fields[Constants.DELIVERY_NUMBER] == '1', (
            'Since Oscar does not provide a street number we set a fake value')
        assert fields[Constants.DELIVERY_CITY] == address.city
        assert fields[Constants.DELIVERY_POSTCODE] == address.postcode
        assert fields[Constants.DELIVERY_STATE] == address.state
        assert fields[Constants.DELIVERY_COUNTRY] == address.country_id

    def test_get_fields_billing(self):
        scaffold = Scaffold()

        address = BillingAddress(
            first_name='First Name',
            last_name='Last Name',
            line1='First Line Address 1',
            line4='Bruxelles',
            postcode='1000',
            country_id='BE')

        order_data = {
            'billing_address': address
        }
        fields = scaffold.get_fields_billing(None, order_data)

        assert Constants.BILLING_STREET in fields
        assert Constants.BILLING_NUMBER in fields
        assert Constants.BILLING_CITY in fields
        assert Constants.BILLING_POSTCODE in fields
        assert Constants.BILLING_STATE in fields
        assert Constants.BILLING_COUNTRY in fields

        assert fields[Constants.BILLING_STREET] == 'First Line Address'
        assert fields[Constants.BILLING_NUMBER] == '1', (
            'Since Oscar does not provide a street number we set a fake value')
        assert fields[Constants.BILLING_CITY] == address.city
        assert fields[Constants.BILLING_POSTCODE] == address.postcode
        assert fields[Constants.BILLING_STATE] == address.state
        assert fields[Constants.BILLING_COUNTRY] == address.country_id

    def test_get_fields_shopper(self):
        scaffold = Scaffold()

        shopper = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
        }

        order_data = {
            'adyen_shopper': shopper
        }
        fields = scaffold.get_fields_shopper(None, order_data)

        assert Constants.SHOPPER_FIRSTNAME in fields
        assert Constants.SHOPPER_INFIX in fields
        assert Constants.SHOPPER_LASTNAME in fields
        assert Constants.SHOPPER_GENDER in fields
        assert Constants.SHOPPER_BIRTH_DAY in fields
        assert Constants.SHOPPER_BIRTH_MONTH in fields
        assert Constants.SHOPPER_BIRTH_YEAR in fields
        assert Constants.SHOPPER_PHONE in fields

        assert fields[Constants.SHOPPER_FIRSTNAME] == 'First Name'
        assert fields[Constants.SHOPPER_INFIX] == ''
        assert fields[Constants.SHOPPER_LASTNAME] == 'Last Name'
        assert fields[Constants.SHOPPER_GENDER] == ''
        assert fields[Constants.SHOPPER_BIRTH_DAY] == ''
        assert fields[Constants.SHOPPER_BIRTH_MONTH] == ''
        assert fields[Constants.SHOPPER_BIRTH_YEAR] == ''
        assert fields[Constants.SHOPPER_PHONE] == ''

        shopper['birthdate'] = datetime.date(1815, 12, 10)
        order_data = {
            'adyen_shopper': shopper
        }
        fields = scaffold.get_fields_shopper(None, order_data)

        assert fields[Constants.SHOPPER_BIRTH_DAY] == '10'
        assert fields[Constants.SHOPPER_BIRTH_MONTH] == '12'
        assert fields[Constants.SHOPPER_BIRTH_YEAR] == '1815'
