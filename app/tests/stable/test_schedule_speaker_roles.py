import datetime as dt

import pytest
from django_scopes import scope

from eventyay.base.models import Room, Submission, SubmissionType, TalkSlot


@pytest.fixture
def schedule(event, user):
    """A released schedule with one session given by `user`, who has a job title and organization."""
    with scope(event=event):
        submission_type = SubmissionType.objects.create(event=event, name='Talk')
        submission = Submission.objects.create(
            title='Keynote', event=event, submission_type=submission_type, content_locale='en'
        )
        submission.speakers.add(user)
        submission.accept()
        submission.confirm()
        room = Room.objects.create(event=event, name='Main Hall')
        slot = {
            'is_visible': True,
            'start': event.date_from + dt.timedelta(hours=10),
            'end': event.date_from + dt.timedelta(hours=11),
            'room': room,
        }
        TalkSlot.objects.update_or_create(submission=submission, schedule=event.wip_schedule, defaults=slot)
        event.release_schedule('v1')
        TalkSlot.objects.update_or_create(submission=submission, schedule=event.current_schedule, defaults=slot)
        profile = user.event_profile(event)
        profile.job_title = 'Founder'
        profile.organization = 'FOSSASIA'
        profile.save()
        return event.current_schedule


def set_public(event, **public):
    """Mark CfP speaker fields as public or not, as on the CfP settings page."""
    for field, value in public.items():
        field_settings = dict(event.cfp.fields.get(field) or {})
        field_settings['public'] = value
        event.cfp.fields[field] = field_settings
    event.cfp.save()


def compact_speaker_role(schedule, user):
    """Return the speaker_role of `user` in the compact schedule data used by the public schedule."""
    with scope(event=schedule.event):
        data = schedule.build_data(compact=True)
    return next(speaker['speaker_role'] for speaker in data['speakers'] if speaker['code'] == user.code)


@pytest.mark.django_db
def test_compact_schedule_includes_public_speaker_role(event, user, schedule):
    """The compact schedule data includes the job title and organization when both are public."""
    set_public(event, job_title=True, organization=True)

    assert compact_speaker_role(schedule, user) == 'Founder, FOSSASIA'


@pytest.mark.django_db
def test_compact_schedule_only_includes_public_role_fields(event, user, schedule):
    """Fields that are not public are left out of the speaker role."""
    set_public(event, job_title=False, organization=True)

    assert compact_speaker_role(schedule, user) == 'FOSSASIA'


@pytest.mark.django_db
def test_compact_schedule_speaker_role_is_empty_when_not_public(event, user, schedule):
    """Without public role fields, the speaker role is empty, so the schedule shows no label."""
    set_public(event, job_title=False, organization=False)

    assert compact_speaker_role(schedule, user) == ''
