import csv
import io

import pytest
from django.test import override_settings
from django_scopes import scopes_disabled


def logs_url(event, query=''):
    return f'/control/event/{event.organizer.slug}/{event.slug}/logs/{query}'


def export_rows(response):
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv'
    return list(csv.reader(io.StringIO(response.content.decode())))


@pytest.fixture
def logs(event, user):
    """30 team actions, more than fit on one page of the log, and one customer action."""
    with scopes_disabled():
        for _ in range(30):
            event.log_action('eventyay.event.changed', user=user)
        event.log_action('eventyay.event.changed')


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_export_contains_every_log_entry(organizer_client, event, logs):
    response = organizer_client.get(logs_url(event, '?download=yes'))

    rows = export_rows(response)
    assert response['Content-Disposition'] == f'attachment; filename="{event.slug}-logs.csv"'
    assert rows[0] == ['Date', 'User', 'Object', 'Action']
    assert len(rows) == 1 + 31
    assert [row[1] for row in rows[1:]].count('Test User') == 30


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_export_keeps_the_current_filter(organizer_client, event, logs):
    team_rows = export_rows(organizer_client.get(logs_url(event, '?user=yes&download=yes')))[1:]
    customer_rows = export_rows(organizer_client.get(logs_url(event, '?user=no&download=yes')))[1:]

    assert len(team_rows) == 30
    assert {row[1] for row in team_rows} == {'Test User'}
    assert len(customer_rows) == 1
    assert customer_rows[0][1] == ''


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_export_does_not_turn_text_into_formulas(organizer_client, event, user):
    with scopes_disabled():
        user.fullname = '=HYPERLINK("https://example.org")'
        user.save()
        event.log_action('eventyay.event.changed', user=user)

    rows = export_rows(organizer_client.get(logs_url(event, '?download=yes')))

    assert rows[1][1] == '\'=HYPERLINK("https://example.org")'


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_logs_page_links_the_export_with_the_current_filter(organizer_client, event, logs):
    response = organizer_client.get(logs_url(event, '?user=yes'))

    assert response.status_code == 200
    assert 'href="?user=yes&amp;download=yes"' in response.content.decode()
