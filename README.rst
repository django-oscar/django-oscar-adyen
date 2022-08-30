==============================
Adyen package for django-oscar
==============================

.. image:: https://img.shields.io/pypi/v/django-oscar-adyen.svg
    :target: https://pypi.python.org/pypi/django-oscar-adyen/
    :alt: Latest Version on PyPI

.. image:: https://img.shields.io/pypi/pyversions/django-oscar-adyen.svg
    :target: https://pypi.python.org/pypi/django-oscar-adyen/
    :alt: Supported Python versions

.. image:: https://img.shields.io/travis/django-oscar/django-oscar-adyen.svg
    :target: https://travis-ci.org/django-oscar/django-oscar-adyen
    :alt: TravisCI status

This package provides integration with the `Adyen`_ payment gateway. It is
designed to work with the e-commerce framework `django-oscar`_. This extension
supports Django 1.8+, Python 3.6+ and Oscar 1.4+.

.. _`Adyen`: http://www.adyen.com/
.. _`django-oscar`: https://github.com/django-oscar/django-oscar


Documentation
=============

https://django-oscar-adyen.readthedocs.io/en/latest/


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
  The URL towards which the Adyen form should be POSTed to initiate the payment
  process (e.g. 'https://test.adyen.com/hpp/select.shtml').
* ``ADYEN_IP_ADDRESS_HTTP_HEADER`` - Optional. The header in `META` to inspect
  to determine the IP address of the request. Defaults to `REMOTE_ADDR`.

You will likely need to specify different settings in your test environment
as opposed to your production environment.

Class-based configuration
-------------------------
In more complex deployments, you will want to e.g. alter the Adyen identifier
based on the request. That is not easily implemented with Django settings, so
you can alternatively set ``ADYEN_CONFIG_CLASS`` to a config class of your own.
See `adyen.settings_config.FromSettingsConfig` for an example.


Changes
=======
0.9.0 - unreleased
------------------

- Upgrade to Oscar 2.0.


0.8.0 - unreleased
------------------

- Add support for OpenInvoice (Klarna, AfterPay)


0.7.1 - released April 19th, 2016
---------------------------------

- Sanitize payment request form fields from newlines

0.7.0 - released April 18th, 2016
---------------------------------

- Add ``adyen.signers`` module to handle signature algorithm
- Refactor how the `merchantSig` is generated, using the new ``adyen.signers``
  module.
- Splits constants and exceptions into their own module
- Handle shopper, billing and delivery fields (with signatures for SHA-1)
- Handle merchantSig with SHA-256 algorithm
- Improve test coverage and other minor changes

This version is backward compatible with version 0.6.0.

Note that plugin users need to implement method ``get_signer_backend`` if they
uses their own config class from the abstract config class.

.. warning::

   The implementation of the signature with SHA-256 algorithm has not been
   tested in a real-life case. Plugin users may use it carefully, and they are
   invited to report any issues they may encounter.

0.6.0 - released March 1st, 2016
--------------------------------

- Allow plugin user to extend it with `get_class`,
- Split several methods in order to override specific parts of the plugin,
- Expose more methods as public methods to allow plugin user to override more
  specific parts of the plugin,
- Add deprecation note on `handle_payment_feedback` and add two separates
  methods to handle payment return case and payment notification case.
- Add `allowedMethods` to the payment request form (unused by default).
- Start a sphinx documentation for the project.

This version is backward compatible with version 0.5.0.

Note that plugin users need to implement method ``get_allowed_methods`` if they
uses their own config class from the abstract config class.

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
