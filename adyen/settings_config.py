from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .config import AbstractAdyenConfig


class FromSettingsConfig(AbstractAdyenConfig):
    """
    This config class is enabled by default and useful in simple deployments.
    One can just set all needed values in the Django settings. It also
    exists for backwards-compatibility with previous deployments.
    """

    def __init__(self):
        """
        We complain as early as possible when Django settings are missing.
        """
        required_settings = [
            'ADYEN_IDENTIFIER', 'ADYEN_ACTION_URL', 'ADYEN_SKIN_CODE', 'ADYEN_SECRET_KEY']
        missing_settings = [
            setting for setting in required_settings if not hasattr(settings, setting)]
        if missing_settings:
            raise ImproperlyConfigured(
                "You are using the FromSettingsConfig config class, but haven't set the "
                "the following required settings: %s" % missing_settings)

    def get_identifier(self, request):
        return settings.ADYEN_IDENTIFIER

    def get_action_url(self, request):
        return settings.ADYEN_ACTION_URL

    def get_skin_code(self, request):
        return settings.ADYEN_SKIN_CODE

    def get_skin_secret(self, request):
        return settings.ADYEN_SECRET_KEY

    def get_ip_address_header(self):
        try:
            return settings.ADYEN_IP_ADDRESS_HTTP_HEADER
        except AttributeError:
            return 'REMOTE_ADDR'
