from django.conf import settings
from django.utils.module_loading import import_string


def get_config():
    """Returns an instance of the configured config class.

    :return: Project's defined Adyen configuration.
    :rtype: :class:`AbstractAdyenConfig`

    By default, this function will return an instance of
    :class:`adyen.settings_config.FromSettingsConfig`. If
    :data:`ADYEN_CONFIG_CLASS` is defined, it will try to load this class and
    return an instance of this class instead.

    .. note::

        This function expects :data:`ADYEN_CONFIG_CLASS` to be a string that
        represent the python import path of the Adyen config class, such as
        ``adyen.settings_config.FromSettingsConfig``.

    """
    try:
        config_class_string = settings.ADYEN_CONFIG_CLASS
    except AttributeError:
        config_class_string = 'adyen.settings_config.FromSettingsConfig'
    return import_string(config_class_string)()


class AbstractAdyenConfig:
    """Abstract class for an Adyen config class.

    Plugin users that want to create their own Adyen config class must comply
    with this interface.
    """
    def get_identifier(self, request):
        """Get Adyen merchant identifier.

        :param request: Django HTTP request object.
        :return: Adyen merchant identifier as string.
        """
        raise NotImplementedError

    def get_action_url(self, request):
        """Get Adyen HPP URL to post payment request form to.

        :param request: Django HTTP request object.
        :return: Adyen HPP URL.
        """
        raise NotImplementedError

    def get_skin_code(self, request):
        """Get Adyen merchant skin code.

        :param request: Django HTTP request object.
        :return: Adyen merchant skin code.
        """
        raise NotImplementedError

    def get_skin_secret(self, request):
        """Get Adyen merchant skin secret key.

        :param request: Django HTTP request object.
        :return: Adyen merchant skin secret key.
        """
        raise NotImplementedError

    def get_ip_address_header(self):
        """Get the request HTTP header used to get customer's IP.

        :return: appropriate request HTTP header.
        """
        raise NotImplementedError

    def get_allowed_methods(self, request, source_type=None):
        """Get customers's list of allowed Adyen payment methods.

        :param request: Django HTTP request object.
        :return: List (or tuple) of allowed payment methods.

        .. versionadded:: 0.6.0

            Make sure to implement this method when using this new version.

        """
        raise NotImplementedError
