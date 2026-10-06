from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone
from django_scopes import scope

from eventyay.base.models import Order


@pytest.fixture
def order(event):
    with scope(organizer=event.organizer):
        return Order.objects.create(
            event=event,
            code='MAILHIST',
            email='buyer@example.org',
            status=Order.STATUS_PAID,
            datetime=timezone.now(),
            expires=timezone.now() + timedelta(days=1),
            total=Decimal('10.00'),
            locale='en',
        )


def order_url(order):
    return f'/control/event/{order.event.organizer.slug}/{order.event.slug}/orders/{order.code}/'


def log_email(order, action_type, message):
    with scope(organizer=order.event.organizer):
        order.log_action(
            action_type,
            data={'subject': 'Your order', 'message': message, 'recipient': order.email},
        )


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_custom_email_is_shown_as_formatted_text(organizer_client, order):
    organizer_client.post(
        order_url(order) + 'sendmail',
        {
            'sendto': order.email,
            'subject': 'Keynote seat',
            'message': '<p>Hello Aisha,</p><p>Your seat is reserved.</p>',
        },
    )

    content = organizer_client.get(order_url(order) + 'mail_history').content.decode()

    assert 'Keynote seat' in content
    assert '<p>Hello Aisha,</p><p>Your seat is reserved.</p>' in content
    assert '&lt;p&gt;' not in content


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_plain_text_email_is_shown_as_paragraphs(organizer_client, order):
    log_email(order, 'eventyay.event.order.email.resend', 'Hello,\n\nyour order is confirmed.')

    content = organizer_client.get(order_url(order) + 'mail_history').content.decode()

    assert '<p>Hello,</p>' in content
    assert '<p>your order is confirmed.</p>' in content


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_email_html_is_sanitized(organizer_client, order):
    log_email(order, 'eventyay.event.order.email.custom_sent', '<p>Hi</p><script>alert(1)</script>')

    content = organizer_client.get(order_url(order) + 'mail_history').content.decode()

    assert '<p>Hi</p>' in content
    assert '<script>alert(1)' not in content


@pytest.mark.django_db
@override_settings(SITE_URL='https://testserver')
def test_remote_images_are_shown_as_links(organizer_client, order):
    qr_image = 'data:image/png;base64,iVBORw0KGgo='
    log_email(
        order,
        'eventyay.event.order.email.custom_sent',
        f'<p><img src="https://images.example.com/banner.png" alt="Banner"></p><p><img src="{qr_image}" alt="QR"></p>',
    )

    content = organizer_client.get(order_url(order) + 'mail_history').content.decode()

    assert '<img alt="Banner"' not in content
    assert 'src="https://images.example.com/banner.png"' not in content
    assert 'href="https://images.example.com/banner.png"' in content
    assert '>Banner</a>' in content
    assert f'src="{qr_image}"' in content
