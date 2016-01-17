from django.conf import settings
from django.utils.module_loading import import_string

# Defines the accepted algorithms. Subclasses should verify that values for ADYEN_HMAC_ALGORITHM
# are contained in this list.
HMAC_ALGORITHMS = ('SHA1', 'SHA256')


def get_config():
    """
    Returns an instance of the configured config class.
    """

    try:
        config_class_string = settings.ADYEN_CONFIG_CLASS
    except AttributeError:
        config_class_string = 'adyen.settings_config.FromSettingsConfig'
    return import_string(config_class_string)()


class AbstractAdyenConfig:
    """
    The base implementation for a config class.
    """

    def get_identifier(self, request):
        raise NotImplementedError

    def get_action_url(self, request):
        raise NotImplementedError

    def get_skin_code(self, request):
        raise NotImplementedError

    def get_skin_secret(self, request):
        raise NotImplementedError

    def get_ip_address_header(self):
        raise NotImplementedError

    def get_hmac_algorithm(self, request):
        raise NotImplementedError
