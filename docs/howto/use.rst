=====
Usage
=====

.. toctree::
   :maxdepth: 2

Basics
======

The main entry point into the plugin is the :class:`adyen.scaffold.Scaffold`
class::

   >>> from adyen.scaffold import Scaffold
   >>> scaffold = Scaffold()

Of course, one can use Oscar's ``get_class`` function instead::

   >>> from oscar.core.loading import get_class
   >>> Scaffold = get_class('adyen.scaffold', 'Scaffold')
   >>> sclaffold = Scaffold()

``Scaffold`` should be the only class used in your application, and you can
consider it as the public interface of the plugin.

Payment form
============

The first step in the Adyen HPP workflow is to generate the form that will be
submitted from your e-commerce site to the Adyen HPP. This form must contain
several fields as described in the Adyen HPP Documentation.

You can get both from the scaffold::

   >>> sclaffold = Scaffold()
   >>> form_action_url = scaffold.get_form_action(request)
   >>> form_fields = scaffold.get_form_fields(request, payment_data)

This should be used in the last view of your checkout before the payment return
view - for example, in ``get_context_data`` to add the form URL and form
fields.

.. seealso::

   You can check the docstring of
   :meth:`adyen.scaffold.Scaffold.get_form_action` and
   :meth:`adyen.scaffold.Scaffold.get_form_fields` for more information.

List of payment data items
--------------------------

+-------------------------+-------------------------+--------------------------------+----------+
| Key                     | Adyen Form Field        | Description                    | Required |
+=========================+=========================+================================+==========+
| ``order_number``        | ``merchantReference``   | Order Number                   | Yes      |
+-------------------------+-------------------------+--------------------------------+----------+
| ``client_id``           | ``shopperReference``    | Customer's identifier          | Yes      |
+-------------------------+-------------------------+--------------------------------+----------+
| ``client_email``        | ``shopperEmail``        | Customer's email               | Yes      |
+-------------------------+-------------------------+--------------------------------+----------+
| ``currency_code``       | ``currencyCode``        | Currency code                  | Yes      |
+-------------------------+-------------------------+--------------------------------+----------+
| ``amount``              | ``paymentAmount``       | Payment amount (in cent)       | Yes      |
+-------------------------+-------------------------+--------------------------------+----------+
| ``shopper_locale``      | ``shopperLocale``       | Customer's locale              | Yes      |
+-------------------------+-------------------------+--------------------------------+----------+
| ``country_code``        | ``countryCode``         | Merchant's Country             | Yes      |
+-------------------------+-------------------------+--------------------------------+----------+
| ``source_type``         | ``allowedMethods``      | Selected ``SourceType`` object | No       |
+-------------------------+-------------------------+--------------------------------+----------+
| ``return_url``          | ``resURL``              | Custom Payment Return URL      | No       |
+-------------------------+-------------------------+--------------------------------+----------+
| ``shipping_address``    | ``deliveryAddress.*``   | Customer shipping address      | No       |
+-------------------------+-------------------------+--------------------------------+----------+
| ``shipping_visibility`` | ``deliveryAddressType`` | Visibility of the address      | No       |
+-------------------------+-------------------------+--------------------------------+----------+
| ``billing_address``     | ``billingAddress.*``    | Customer billing address       | No       |
+-------------------------+-------------------------+--------------------------------+----------+
| ``billing_visibility``  | ``billingAddressType``  | Visibility of the address      | No       |
+-------------------------+-------------------------+--------------------------------+----------+

Both ``shipping_address`` and ``billing_address`` are expected to be standard
shipping and billing Django-Oscar address objects.

The ``shipping_visibility`` and ``billing_visibility`` take the values defined
in the Adyen documentation: 1 for visible but not editable and 2 for not
visible. By default, 2 is used by the plugin.


Handle payment return
=====================

When customers authorise a payment through the Adyen HPP, they are redirected
back to your e-commerce site with a payment status that can be used to record
the transaction (successful or not).

As usual, everything is handled with the scaffold::

   >>> sclaffold = Scaffold()
   >>> result = sclaffold.handle_payment_return(request)
   >>> success, status, details = result

This can be done in the payment return view, to determine what to display to
the customer: a thank-you or sorry page, depending on the value of ``success``
for example.

If you didn't place the order yet, it should be the right place to do it - if
not the last possible one.

In any case, it's up to you to decide if you want to handle the payment here or
if you want to wait for the payment notification.

.. seealso::

   You can check the docstring of
   :meth:`adyen.scaffold.Scaffold.handle_payment_return` for more information.


Register payment notification
=============================

Eventually Adyen will send to your Payment Notification URL a ``POST`` request
to notify your application of a transaction. Since you may already have
recorded the transaction, you need to assess the relevance of the notification,
and then handle it.

The same way you handled payment return, you can handle payment notification::

   >>> sclaffold = Scaffold()
   >>> result = sclaffold.handle_payment_notification(request)
   >>> success, status, details = result

With Adyen Payment Notification, your application must expose an URL accessible
through a ``POST`` request. This view is the right place to call this method,
but it is up to you to decide if you want to handle the payment here, modify
the order, or ignore it if already done in the payment return view.

.. seealso::

   You can check the docstring of
   :meth:`adyen.scaffold.Scaffold.handle_payment_notification` for more
   information.
