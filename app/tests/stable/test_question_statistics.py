from datetime import timedelta
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup
from django.test import override_settings
from django.utils import timezone
from django_scopes import scope

from eventyay.base.models import Order, OrderPosition, Product, Question, QuestionAnswer


@pytest.fixture
def answered_question(event):
    with scope(organizer=event.organizer, event=event):
        ticket = Product.objects.create(event=event, name='Ticket', default_price=10, admission=True)
        workshop = Product.objects.create(event=event, name='Workshop', default_price=5, admission=False)
        question = Question.objects.create(event=event, question='Company', type=Question.TYPE_STRING)
        question.products.add(ticket, workshop)
        order = Order.objects.create(
            event=event,
            code='FOO',
            email='buyer@example.org',
            status=Order.STATUS_PAID,
            datetime=timezone.now(),
            expires=timezone.now() + timedelta(days=1),
            total=10,
            locale='en',
        )
        position = OrderPosition.objects.create(order=order, product=ticket, price=Decimal('10'))
        QuestionAnswer.objects.create(orderposition=position, question=question, answer='ACME Corp')
    return question, ticket, workshop


def statistics_url(event, question):
    return f'/control/event/{event.organizer.slug}/{event.slug}/questions/{question.pk}/'


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_question_statistics_filter_by_product(organizer_client, event, answered_question):
    question, ticket, workshop = answered_question
    url = statistics_url(event, question)

    response = organizer_client.get(f'{url}?product={ticket.pk}')
    assert response.status_code == 200
    assert 'ACME Corp' in response.content.decode()

    response = organizer_client.get(f'{url}?product={workshop.pk}')
    assert response.status_code == 200
    assert 'ACME Corp' not in response.content.decode()


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_question_statistics_keeps_product_in_filter_and_links(organizer_client, event, answered_question):
    question, ticket, _workshop = answered_question

    response = organizer_client.get(f'{statistics_url(event, question)}?product={ticket.pk}')
    doc = BeautifulSoup(response.content.decode(), 'lxml')

    select = doc.find('select', attrs={'name': 'product'})
    assert select.find('option', selected=True)['value'] == str(ticket.pk)
    answer_link = doc.select_one('#question-stats a[href*="/orders/"]')
    assert f'product={ticket.pk}' in answer_link['href']
