==============================
Adyen package for django-oscar
==============================

.. image:: https://img.shields.io/pypi/v/django-oscar-adyen.svg
    :target: https://pypi.python.org/pypi/django-oscar-adyen/
    :alt: Latest Version on PyPI

.. image:: https://img.shields.io/pypi/pyversions/django-oscar-adyen.svg
    :target: https://pypi.python.org/pypi/django-oscar-adyen/
    :alt: Supported Python versions

.. image:: https://img.shields.io/travis/oscaro/django-oscar-adyen.svg
    :target: https://travis-ci.org/oscaro/django-oscar-adyen
    :alt: TravisCI status

This package provides integration with the `Adyen`_ payment gateway. It is
designed to work seamlessly with the e-commerce framework `django-oscar`_, but
can be used without Oscar. This extension supports Django 1.7+, Python 3.3+ and
Oscar 1.0+.

.. _`Adyen`: http://www.adyen.com/
.. _`django-oscar`: https://github.com/django-oscar/django-oscar


Installation
============

Get it from PyPi::

    $ pip install django-oscar-adyen


Add ``'adyen'`` to ``INSTALLED_APPS`` and run::

    $ django-admin migrate adyen

to create the appropriate database tables.

Configuration
=============

You have two approaches to configure `django-oscar-adyen`.

Settings-based configuration
----------------------------
For simple deployments, setting the required values in the settings will suffice.

Edit your ``settings.py`` to set the following settings:

* ``ADYEN_IDENTIFIER`` - The identifier of your Adyen account.
* ``ADYEN_SKIN_CODE`` -  The code for your Adyen skin.
* ``ADYEN_SECRET_KEY`` - The secret key defined in your Adyen skin.
* ``ADYEN_ACTION_URL`` -
  The URL towards which the Adyen form should be POSTed to initiate the payment process
  (e.g. 'https://test.adyen.com/hpp/select.shtml').
* ``ADYEN_IP_ADDRESS_HTTP_HEADER`` - Optional. The header in `META` to inspect to determine
  the IP address of the request. Defaults to `REMOTE_ADDR`.

You will likely need to specify different settings in your test environment
as opposed to your production environment.

Class-based configuration
-------------------------
In more complex deployments, you will want to e.g. alter the Adyen identifier based on
the request. That is not easily implemented with Django settings, so you can alternatively
set ``ADYEN_CONFIG_CLASS`` to a config class of your own.
See `adyen.settings_config.FromSettingsConfig` for an example.

Changes
=======

0.5.0 - released October 7th, 2015
----------------------------------
- Add support for Adyen's `ERROR` and `PENDING` payment statuses
  (https://github.com/oscaro/django-oscar-adyen/pull/20). This means two additional payment
  statuses for the `Scaffold` interface; please adapt your code as needed when upgrading.

0.4.2 - released September 29, 2015
-----------------------------------
- Acknowledge, but don't process Adyen's test notifications
  (https://github.com/oscaro/django-oscar-adyen/pull/18)

0.4.1 - released September 24, 2015
-----------------------------------
- ignore additional data sent by Adyen's new-style system communications
  (https://github.com/oscaro/django-oscar-adyen/pull/17)

0.4.0 - released July 14th, 2015
--------------------------------

- change scaffold interface (https://github.com/oscaro/django-oscar-adyen/pull/16)
- ignore duplicate Adyen notifications (https://github.com/oscaro/django-oscar-adyen/pull/16)

0.3.0 - released July 8th, 2015
-------------------------------

- Django 1.8 and Oscar 1.1 support (#https://github.com/oscaro/django-oscar-adyen/pull/15)
- introduce config classes for dynamic configuration (https://github.com/oscaro/django-oscar-adyen/pull/14)


License
=======

``django-oscar-adyen`` is released under the BSD license, like Django itself.
