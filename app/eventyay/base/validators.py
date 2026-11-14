from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

from eventyay import consts


class BanlistValidator:
    banlist = []

    def __call__(self, value):
        # Validation logic
        if value in self.banlist:
            raise ValidationError(
                _('This field has an invalid value: %(value)s.'),
                code='invalid',
                params={'value': value},
            )


@deconstructible
class EventSlugBanlistValidator(BanlistValidator):
    banlist = [
        'download',
        'healthcheck',
        'locale',
        'control',
        'redirect',
        'jsi18n',
        'metrics',
        '_global',
        '__debug__',
        'api',
        'events',
        'csp_report',
        'widget',
    ]


@deconstructible
class OrganizerSlugBanlistValidator(BanlistValidator):
    # An organizer's pages live at /<organizer>/ and /<organizer>/<event>/. A short form that is also a
    # top-level path would show that path's page instead. tests/stable/test_organizer_slug_banlist.py
    # checks this list against the URLs.
    banlist = [
        'invite',
        'download',
        'healthcheck',
        'locale',
        'control',
        'pretixdroid',
        'redirect',
        'jsi18n',
        'metrics',
        '_global',
        '__debug__',
        'about',
        'api',
        'csp_report',
        'widget',
        'admin',
        'all-events',
        'common',
        'exhibitor-invitation',
        'followed-events',
        'login',
        'media',
        'orga',
        'page',
        'past',
        'privacy',
        'static',
        'support',
        'terms',
        'upcoming',
    ]


@deconstructible
class EmailBanlistValidator(BanlistValidator):
    banlist = [
        consts.EVENTYAY_EMAIL_NONE_VALUE,
    ]
