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


.. data:: ADYEN_ACTION_URL

  The URL towards which the Adyen form should be POSTed to initiate the payment
  process. (e.g. ``https://test.adyen.com/hpp/select.shtml``).


.. data:: ADYEN_IP_ADDRESS_HTTP_HEADER

   Optional. The header in ``META`` to inspect to determine the IP address of
   the request. Defaults to ``REMOTE_ADDR``.

You will likely need to specify different settings in your test environment
as opposed to your production environment.

Class-based configuration
=========================

In more complex deployments, you will want to e.g. alter the Adyen identifier
based on the request (country, language, users, etc.). That is not easily
implemented with Django settings, so you can alternatively set
``ADYEN_CONFIG_CLASS`` to a config class of your own.

.. seealso::

   :class:`adyen.settings_config.FromSettingsConfig` is the default class used
   to handle your Adyen configuration.
