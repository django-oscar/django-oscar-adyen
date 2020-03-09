from django.utils.translation import ugettext_lazy as _

from oscar.core.application import OscarConfig


class AdyenConfig(OscarConfig):
    label = 'adyen'
    name = 'adyen'
    verbose_name = _('Adyen')
