import unittest

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings

# We use get_config() instead of adyen_config because throughout
# the tests, we repeatedly change the Django settings.
from adyen.config import AbstractAdyenConfig, get_config
from adyen.settings_config import FromSettingsConfig


class TestAbstractAdyenConfig(unittest.TestCase):
    def test_get_identifier(self):
        request = RequestFactory()
        config = AbstractAdyenConfig()
        with self.assertRaises(NotImplementedError):
            config.get_identifier(request)

    def test_get_action_url(self):
        request = RequestFactory()
        config = AbstractAdyenConfig()
        with self.assertRaises(NotImplementedError):
            config.get_action_url(request)

    def test_get_skin_code(self):
        request = RequestFactory()
        config = AbstractAdyenConfig()
        with self.assertRaises(NotImplementedError):
            config.get_skin_code(request)

    def test_get_skin_secret(self):
        request = RequestFactory()
        config = AbstractAdyenConfig()
        with self.assertRaises(NotImplementedError):
            config.get_skin_secret(request)

    def test_get_ip_address_header(self):
        config = AbstractAdyenConfig()
        with self.assertRaises(NotImplementedError):
            config.get_ip_address_header()

    def test_get_allowed_methods(self):
        request = RequestFactory()
        config = AbstractAdyenConfig()
        with self.assertRaises(NotImplementedError):
            config.get_allowed_methods(request, source_type=None)


@override_settings(
    ADYEN_IDENTIFIER='foo',
    ADYEN_SECRET_KEY='foo',
    ADYEN_ACTION_URL='foo',
    ADYEN_SKIN_CODE='foo',
)
class TestFromSettings(TestCase):
    """
    This test case tests the FromSettings config class, which just fetches its
    values from the Django settings.
    """

    def test_is_default(self):
        assert isinstance(get_config(), FromSettingsConfig)

    def test_value_passing_works(self):
        assert get_config().get_action_url(None) == 'foo'

    # https://docs.djangoproject.com/en/1.8/topics/testing/tools/#django.test.modify_settings
    # Override settings is needed to let us delete settings on a per-test basis.
    @override_settings()
    def test_complains_when_not_fully_configured(self):
        # If the setting is missing, a proper exception is raised
        del settings.ADYEN_ACTION_URL
        with self.assertRaises(ImproperlyConfigured):
            get_config()

    def test_get_ip_address_header_default(self):
        config = get_config()
        assert config.get_ip_address_header() == 'REMOTE_ADDR'

    @override_settings(ADYEN_IP_ADDRESS_HTTP_HEADER='X_FORWARDED_FOR')
    def test_get_ip_address_header_by_settings(self):
        config = get_config()
        assert config.get_ip_address_header() == 'X_FORWARDED_FOR'

    def test_get_allowed_methods_default(self):
        config = get_config()
        request = RequestFactory()
        assert config.get_allowed_methods(request, None) is None

    @override_settings(ADYEN_ALLOWED_METHODS=('card', 'bankTransfer'))
    def test_get_allowed_methods_by_settings(self):
        config = get_config()
        request = RequestFactory()
        expected = ('card', 'bankTransfer')
        assert config.get_allowed_methods(request, None) == expected


class DummyConfigClass(AbstractAdyenConfig):

    def get_action_url(self, request):
        return 'foo'


@override_settings(ADYEN_CONFIG_CLASS='tests.test_config.DummyConfigClass')
class CustomConfigClassTestCase(TestCase):
    """
    This test case checks that it's possible to replace the FromSettings confic class
    by one's own, and that it is used to fetch values as expected.
    """

    def test_class_gets_picked_up(self):
        assert isinstance(get_config(), DummyConfigClass)

    @override_settings(ADYEN_ACTION_URL='bar')
    def test_settings_ignored(self):
        """
        Check that we indeed ignore Django settings (apart from the config class).
        """
        assert get_config().get_action_url(None) == 'foo'
