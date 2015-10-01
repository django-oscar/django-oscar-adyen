# -*- coding: utf-8 -*-

from unittest.mock import Mock

from copy import deepcopy

from django.test import TestCase

from adyen.gateway import MissingFieldException, PaymentNotification, \
    Constants, UnexpectedFieldException
from adyen.scaffold import Scaffold

AUTHORISED_PAYMENT_PARAMS_POST = {
    'currency': 'EUR',
    'eventCode': 'AUTHORISATION',
    'live': 'false',
    'eventDate': '2014-10-18T17:00:00.00Z',
    'merchantAccountCode': 'OscaroBE',
    'merchantReference': '789:456:00000000123',
    'operations': 'CANCEL,CAPTURE,REFUND',
    'originalReference': '',
    'paymentMethod': 'visa',
    'pspReference': '7914120802434172',
    'reason': '32853:1111:6/2016',
    'success': 'true',
    'value': '21714',
}


class TestAdyenPaymentNotification(TestCase):
    """
    Test case that tests Adyen payment notifications (Adyen servers POST'ing to us)
    """

    def setUp(self):
        super().setUp()
        request = Mock()
        request.method = 'POST'
        # Most tests use unproxied requests, the case of proxied ones
        # is unit-tested by the `test_get_origin_ip_address` method.
        request.META = {'REMOTE_ADDR': '127.0.0.1'}
        request.POST = deepcopy(AUTHORISED_PAYMENT_PARAMS_POST)
        self.request = request

    def test_valid_request(self):
        """
        If this is an `AUTHORISATION` request targeting the proper platform,
        we should both process and acknowledge it. This test is needed
        as a base assumption for the tests below.
        """
        assert (True, True) == Scaffold().assess_notification_relevance(self.request)

    def test_platform_mismatch_live_notification(self):
        """
        If there is a mismatch between the request origin and target platforms,
        we should just let it be.
        """
        self.request.POST['live'] = 'true'
        assert (False, False) == Scaffold().assess_notification_relevance(self.request)

    def test_platform_mismatch_live_server(self):
        self.request.POST['live'] = 'false'
        with self.settings(ADYEN_ACTION_URL='https://live.adyen.com/hpp/select.shtml'):
            assert (False, False) == Scaffold().assess_notification_relevance(self.request)

    def test_non_authorisation(self):
        """
        If this is not an `AUTHORISATION` request, we should acknowledge it
        but not try to process it.
        """
        self.request.POST[Constants.EVENT_CODE] = 'REPORT_AVAILABLE'
        assert (False, True) == Scaffold().assess_notification_relevance(self.request)

    def test_duplicate_notifications(self):
        """
        This test tests that duplicate notifications are ignored.
        """
        # We have a valid request. So let's confirm that we think we should process
        # and acknowledge it.
        assert (True, True) == Scaffold().assess_notification_relevance(self.request)

        # Let's process it then.
        __, __, __ = Scaffold().handle_payment_feedback(self.request)

        # As we have already processed that request, we now shouldn't process the request
        # any more. But we still acknowledge it.
        assert (False, True) == Scaffold().assess_notification_relevance(self.request)

    def test_test_notification(self):
        """
        Adyen can send test notifications even to the live system for debugging
        connection problems. We should acknowledge them, but not process.
        """
        self.request.POST[Constants.PSP_REFERENCE] = Constants.TEST_REFERENCE_PREFIX + '_5'
        assert (False, True) == Scaffold().assess_notification_relevance(self.request)


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
