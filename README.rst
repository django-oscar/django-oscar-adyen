==============================
Adyen package for django-oscar
==============================

.. image:: https://pypip.in/version/django-oscar-adyen/badge.svg
    :target: https://pypi.python.org/pypi/django-oscar-adyen/
    :alt: Latest Version

.. image:: https://pypip.in/py_versions/django-oscar-adyen/badge.svg
    :target: https://pypi.python.org/pypi/django-oscar-adyen/
    :alt: Supported Python versions

.. image:: https://api.travis-ci.org/oscaro/django-oscar-adyen.svg
    :target: https://travis-ci.org/oscaro/django-oscar-adyen

This package provides integration with the `Adyen`_ payment gateway. It is
designed to work seamlessly with the e-commerce framework `django-oscar`_ but
can be used without Oscar. This extension supports Django 1.6+, Python 3.3+ and
Oscar 0.7+.

.. _`Adyen`: http://www.adyen.com/
.. _`django-oscar`: https://github.com/tangentlabs/django-oscar


Getting started
===============

Installation
------------

From PyPi::

    $ pip install django-oscar-adyen

or from Github::

    $ pip install git+git://github.com/oscaro/django-oscar-adyen.git#egg=django-oscar-adyen

Add ``'adyen'`` to ``INSTALLED_APPS`` and run::

    $ django-admin migrate adyen

to create the appropriate database tables.

Configuration
-------------

Edit your ``settings.py`` to set the following settings:

.. code-block:: python

    ADYEN_IDENTIFIER = 'YourAdyenAccountName'
    ADYEN_SECRET_KEY = 'YourAdyenSkinSecretKey'
    ADYEN_ACTION_URL = 'https://test.adyen.com/hpp/select.shtml'

Obviously, you'll need to specify different settings in your test environment
as opposed to your production environment.


Settings
========

====================== =========================================================
 Setting                Description
---------------------- ---------------------------------------------------------
 ``ADYEN_IDENTIFIER``   The identifier of your Adyen account
 ``ADYEN_SECRET_KEY``   The secret key defined in your Adyen skin
 ``ADYEN_ACTION_URL``   The URL towards which the Adyen form should be POSTed
                        to initiate the payment process
====================== =========================================================

License
=======

``django-oscar-adyen`` is released under the BSD license, like Django itself.
