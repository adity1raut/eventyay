"""Regression tests for the missing BILLING_REMINDER_SCHEDULE setting.

``collect_billing_invoice()`` reads ``settings.BILLING_REMINDER_SCHEDULE`` while building
the ``BillingInvoice`` kwargs. The setting was never defined, so the read raised
``AttributeError`` before ``billing_invoice.save()`` could run. Since that constructor is
the only place a ``BillingInvoice`` is created, no invoice ever reached the database, and
``monthly_billing_collect()`` catches only ``DatabaseError`` so the failure took down the
whole run rather than a single event.

These tests keep the setting defined, keep its values usable, and keep the two functions
that consume it able to accept it.
"""

import calendar
from datetime import datetime

import pytest
from django.conf import settings

from eventyay.base.models.billing import BillingInvoice
from eventyay.eventyay_common.tasks import get_next_reminder_datetime


def test_setting_is_defined():
    """The read that used to raise AttributeError must now resolve."""
    assert hasattr(settings, 'BILLING_REMINDER_SCHEDULE')


def test_setting_is_a_non_empty_list_of_ints():
    schedule = settings.BILLING_REMINDER_SCHEDULE
    assert isinstance(schedule, list)
    assert schedule, 'an empty schedule leaves invoices with no reminder at all'
    assert all(isinstance(day, int) for day in schedule)


@pytest.mark.parametrize('month', range(1, 13))
def test_every_day_exists_in_every_month(month):
    """check_billing_status_for_warning() and retry_failed_payment() build
    datetime(year, month, day) directly from these values, so a day past the
    shortest month's length raises ValueError and aborts the whole task."""
    days_in_month = calendar.monthrange(2026, month)[1]
    for day in settings.BILLING_REMINDER_SCHEDULE:
        assert 1 <= day <= days_in_month, (
            f'day {day} does not exist in month {month}; datetime(2026, {month}, {day}) would raise ValueError'
        )
        datetime(2026, month, day)


def test_get_next_reminder_datetime_accepts_the_setting():
    """Line 144 of collect_billing_invoice passes the setting straight into this helper."""
    result = get_next_reminder_datetime(list(settings.BILLING_REMINDER_SCHEDULE))
    assert isinstance(result, datetime)


def test_reminder_schedule_field_accepts_the_setting():
    """Guards against the model field being renamed out from under the setting."""
    field = BillingInvoice._meta.get_field('reminder_schedule')
    field.clean(list(settings.BILLING_REMINDER_SCHEDULE), None)
