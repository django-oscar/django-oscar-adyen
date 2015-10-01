from django.test import override_settings, TestCase
from adyen.facade import Facade
from adyen.gateway import PaymentNotification, Constants, MissingFieldException, \
    UnexpectedFieldException
from tests import MockRequest


def test_is_valid_ip_address():
    # Valid IPv4 and IPv6 addresses
    valid_addresses = ['127.0.0.1', '192.168.12.34', '2001:0db8:85a3:0000:0000:8a2e:0370:7334']
    for address in valid_addresses:
        assert Facade._is_valid_ip_address(address)

    # Empty string, noise, IPv4 out of range, invalid IPv6-lookalike
    invalid_addresses = ['', 'TOTORO', '192.168.12.345', '2001::0234:C1ab::A0:aabc:003F']
    for address in invalid_addresses:
        assert not Facade._is_valid_ip_address(address)


TEST_IP_ADDRESS_HTTP_HEADER = 'HTTP_X_FORWARDED_FOR'


def test_get_origin_ip_address():
    """
    Make sure that the `_get_origin_ip_address()` method works with all
    the possible meaningful combinations of default and custom HTTP header
    names.
    """
    get_ip_address = Facade()._get_origin_ip_address
    # With no specified ADYEN_IP_ADDRESS_HTTP_HEADER setting,
    # ensure we fetch the origin IP address in the REMOTE_ADDR
    # HTTP header.
    assert '127.0.0.1' == get_ip_address(MockRequest())

    # Check the return value is None if we have nothing
    # in the `REMOTE_ADDR` header.
    assert get_ip_address(MockRequest(remote_address='')) is None

    # Check the return value is None if we have no `REMOTE_ADDR`
    # header at all.
    assert get_ip_address(MockRequest(remote_address=None)) is None

    with override_settings(ADYEN_IP_ADDRESS_HTTP_HEADER=TEST_IP_ADDRESS_HTTP_HEADER):
        # Now we add the `HTTP_X_FORWARDED_FOR` header and
        # ensure it is used instead.
        request = MockRequest()
        request.META.update({
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_X_FORWARDED_FOR': '93.16.93.168'
        })
        assert '93.16.93.168' == get_ip_address(request)

        # Even if the default header is missing.
        del request.META['REMOTE_ADDR']
        assert '93.16.93.168' == Facade()._get_origin_ip_address(request)

        # And finally back to `None` if we have neither header.
        del request.META['HTTP_X_FORWARDED_FOR']
        assert Facade()._get_origin_ip_address(request) is None


class MockClient:
    secret_key = None


class PaymentNotificationTestCase(TestCase):

    def create_mock_notification(self, required=True, optional=False, additional=False):
        keys_to_set = []
        if required:
            keys_to_set += PaymentNotification.REQUIRED_FIELDS
        if optional:
            keys_to_set += PaymentNotification.OPTIONAL_FIELDS
        if additional:
            keys_to_set += [Constants.ADDITIONAL_DATA_PREFIX + 'foo']
        params = {key: 'FOO' for key in keys_to_set}

        return PaymentNotification(MockClient(), params)

    def test_required_fields_are_required(self):
        notification = self.create_mock_notification(
            required=False, optional=True, additional=True)
        with self.assertRaises(MissingFieldException):
            notification.check_fields()

    def test_unknown_fields_cause_exception(self):
        notification = self.create_mock_notification(
            required=True, optional=False, additional=False)
        notification.params['UNKNOWN_FIELD'] = 'foo'

        with self.assertRaises(UnexpectedFieldException):
            notification.check_fields()

    def test_optional_fields_are_optional(self):
        notification = self.create_mock_notification(
            required=True, optional=False, additional=False)

        notification.check_fields()

    def test_additional_fields_are_ignored(self):
        notification = self.create_mock_notification(
            required=True, optional=False, additional=True)

        notification.check_fields()
