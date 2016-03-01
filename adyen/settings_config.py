from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .config import AbstractAdyenConfig


class FromSettingsConfig(AbstractAdyenConfig):
    """Manage Plugin's configuration from the project's settings.

    It gets all information required by the plugin from the project's settings,
    and can be used as a base class for specific cases.

    The expected settings are:

    * :data:`ADYEN_IDENTIFIER`
    * :data:`ADYEN_ACTION_URL`
    * :data:`ADYEN_SKIN_CODE`
    * :data:`ADYEN_SECRET_KEY`

    """
    def __init__(self):
        """Initialize configuration and check project's settings.

        We complain as early as possible when Django settings are missing.
        """
        required_settings = [
            'ADYEN_IDENTIFIER',
            'ADYEN_ACTION_URL',
            'ADYEN_SKIN_CODE',
            'ADYEN_SECRET_KEY']

        missing_settings = [
            setting
            for setting in required_settings
            if not hasattr(settings, setting)]

        if missing_settings:
            raise ImproperlyConfigured(
                "You are using the FromSettingsConfig config class, "
                "but haven't set the the following required settings: %s"
                % missing_settings)

    def get_identifier(self, request):
        """Return :data:`ADYEN_IDENTIFIER`."""
        return settings.ADYEN_IDENTIFIER

    def get_action_url(self, request):
        """Return :data:`ADYEN_ACTION_URL`."""
        return settings.ADYEN_ACTION_URL

    def get_skin_code(self, request):
        """Return :data:`ADYEN_SKIN_CODE`."""
        return settings.ADYEN_SKIN_CODE

    def get_skin_secret(self, request):
        """Return :data:`ADYEN_SECRET_KEY`."""
        return settings.ADYEN_SECRET_KEY

    def get_ip_address_header(self):
        """Return :data:`ADYEN_IP_ADDRESS_HTTP_HEADER` or ``REMOTE_ADDR``.

        If the setting is not configured, the default value ``REMOTE_ADDR`` is
        returned instead.
        """
        try:
            return settings.ADYEN_IP_ADDRESS_HTTP_HEADER
        except AttributeError:
            return 'REMOTE_ADDR'

    def get_allowed_methods(self, request, source_type=None):
        """Return :data:`ADYEN_ALLOWED_METHODS` or ``None``.

        :param request: Django HTTP request object.
        :param source_type: A ``SourceType`` object or ``None``.

        If the setting is not configured, the default value ``None`` is
        returned instead. It means the application does not specify any allowed
        methods so customers can select a payment methods on the Adyen HPP
        itself.

        Note that both ``request`` and ``source_type`` parameters are ignored
        and only the setting matters.
        """
        try:
            return settings.ADYEN_ALLOWED_METHODS
        except AttributeError:
            return None
