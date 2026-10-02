import re

import pytest


def page_title(response):
    title = re.search(r'<title>(.*?)</title>', response.content.decode(), re.S).group(1)
    return ' '.join(title.split())


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('query', 'heading'),
    [('', 'Event list'), ('?style=calendar', 'Event overview'), ('?style=week', 'Event overview')],
)
def test_organizer_page_title_separates_page_and_organizer(client, organizer, event, query, heading):
    response = client.get(f'/{organizer.slug}/{query}')

    assert response.status_code == 200
    assert page_title(response).startswith(f'{heading} :: {organizer.name} :: ')


@pytest.mark.django_db
def test_event_page_title_names_the_event_once(client, organizer, event):
    response = client.get(f'/{organizer.slug}/{event.slug}/')

    assert response.status_code == 200
    title = page_title(response)
    assert title.startswith(f'{event.name} :: ')
    assert title.count(str(event.name)) == 1


@pytest.mark.django_db
def test_event_subpage_title_separates_page_and_event(client, organizer, event):
    response = client.get(f'/{organizer.slug}/{event.slug}/resend/')

    assert response.status_code == 200
    assert page_title(response).startswith(f'Resend order links :: {event.name} :: ')
