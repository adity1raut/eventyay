import re
from importlib import import_module

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import Resolver404, resolve, reverse

from eventyay.base.models import Organizer
from eventyay.base.validators import OrganizerSlugBanlistValidator


SLUG_PATTERN = r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?'


def first_path_segments(patterns):
    for pattern in patterns:
        route = str(pattern.pattern).lstrip('^')
        if not route and hasattr(pattern, 'url_patterns'):
            yield from first_path_segments(pattern.url_patterns)
        else:
            yield re.split(r'[/$?(\\]', route, maxsplit=1)[0]


def view_name(path):
    try:
        return resolve(path).view_name
    except Resolver404:
        return None


def test_organizer_short_forms_cannot_match_app_paths():
    # An organizer's pages live at /<organizer>/ and /<organizer>/<event>/. When another page is served
    # at one of those paths, the organizer or its events can't be reached, so the short form must be banned.
    urlconf = import_module(settings.ROOT_URLCONF)
    segments = {segment for segment in first_path_segments(urlconf.urlpatterns) if re.fullmatch(SLUG_PATTERN, segment)}
    taken = {
        segment
        for segment in segments
        if view_name(f'/{segment}/') != 'presale:organizer.index'
        or view_name(f'/{segment}/example-event/') != 'presale:event.index'
    }
    # The web server serves static and media files before a request reaches Django.
    taken |= {settings.STATIC_URL.strip('/'), settings.MEDIA_URL.strip('/')}
    assert sorted(taken - set(OrganizerSlugBanlistValidator.banlist)) == []


@pytest.mark.django_db
@pytest.mark.parametrize('slug', ['common', 'admin', 'orga', 'past'])
def test_app_paths_are_rejected_as_organizer_short_forms(client, slug):
    with pytest.raises(ValidationError):
        Organizer._meta.get_field('slug').run_validators(slug)
    response = client.get(reverse('organizer_request.slug'), {'slug': slug})
    assert response.json()['available'] is False
