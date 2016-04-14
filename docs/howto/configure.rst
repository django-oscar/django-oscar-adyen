=========
Configure
=========

.. toctree::
   :maxdepth: 2


You have two approaches to configure `django-oscar-adyen`.

Settings-based configuration
============================

For simple deployments, setting the required values in the settings will
suffice.

Edit your ``settings.py`` to set the following settings:


.. data:: ADYEN_IDENTIFIER

   Your Adyen Account's identifier.


.. data:: ADYEN_SKIN_CODE

   Your Adyen Skin's code.


.. data:: ADYEN_SECRET_KEY

   Your Adyen Skin's secret key.


.. data:: ADYEN_SIGNER_BACKEND

   The Signer backend class as a python path. The signer will be responsible
   for computing hash for signatures used in the payment request form, and to
   verify the payment return URL's result.

   By default ``adyen.signers.HMACSha1`` is used, which implement the SHA-1
   legacy signature for Adyen.

   .. versionadded:: 0.7.0


.. data:: ADYEN_ACTION_URL

   The URL towards which the Adyen form should be POSTed to initiate the payment
   process. (e.g. ``https://test.adyen.com/hpp/select.shtml``).


.. data:: ADYEN_IP_ADDRESS_HTTP_HEADER

   Optional. The header in ``META`` to inspect to determine the IP address of
   the request. Defaults to ``REMOTE_ADDR``.


.. data:: ADYEN_ALLOWED_METHODS

   Optional. If provided, it must be a tuple of available payment methods as
   defined in the Adyen interface. If not defined, customers will select a
   payment method on the HPP without restriction.

   .. versionadded:: 0.6.0


You will likely need to specify different settings in your test environment
as opposed to your production environment.

Class-based configuration
=========================

In more complex deployments, you will want to e.g. alter the Adyen identifier
based on the request (country, language, users, etc.). That is not easily
implemented with Django settings, so you can alternatively set
``ADYEN_CONFIG_CLASS`` to a config class of your own:

.. data:: ADYEN_CONFIG_CLASS

   Optional. Define the class used to instantiate the Adyen config. If defined
   this settings **must** be the import path of the class as a string, for
   example ``adyen.settings_config.FromSettingsConfig``.

Internaly, this plugin uses :class:`~adyen.settings_config.FromSettingsConfig`
to handle the configuration. Plugin users can extends this class for their
needs and set the :data:`ADYEN_CONFIG_CLASS` settings to use it.
