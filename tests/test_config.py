from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from django.test import TestCase
from django.test.utils import override_settings

# We use get_config() instead of adyen_config because throughout
# the tests, we repeatedly change the Django settings.
from adyen.config import get_config, AbstractAdyenConfig
from adyen.settings_config import FromSettingsConfig


@override_settings(
    ADYEN_IDENTIFIER='foo',
    ADYEN_SECRET_KEY='foo',
    ADYEN_ACTION_URL='foo',
    ADYEN_SKIN_CODE='foo',
)
class FromSettingsTestCase(TestCase):
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


