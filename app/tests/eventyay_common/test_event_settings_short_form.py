"""Tests for the Short form field on the event settings page."""

import bs4
import pytest
from django.test import override_settings
from django.urls import reverse


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_short_form_shows_the_event_address(organizer_client, event):
    """The short form is shown inside the event's address, as on the create event page, not after a lone '/'."""
    url = reverse('eventyay_common:event.update', kwargs={'organizer': event.organizer.slug, 'event': event.slug})
    response = organizer_client.get(url)
    assert response.status_code == 200

    doc = bs4.BeautifulSoup(response.content, 'lxml')
    widget = doc.select_one('.slug-widget')
    assert (
        widget.select_one('.slug-widget-prefix').get_text(strip=True) == f'https://testserver/{event.organizer.slug}/'
    )
    assert widget.select_one('input[name=slug]')['value'] == event.slug
