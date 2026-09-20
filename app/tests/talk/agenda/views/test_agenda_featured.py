import pytest
from django.contrib.auth.models import AnonymousUser
from django_scopes import scope

from eventyay.base.models import Event
from eventyay.common.templatetags.event_tags import can_view_featured_sessions_public
from eventyay.talk_rules.submission import are_featured_submissions_visible


@pytest.mark.django_db
@pytest.mark.parametrize("featured", ("always", "never", "until_schedule", "after_schedule"))
def test_featured_invisible_because_setting(
    client, django_assert_max_num_queries, event, featured, confirmed_submission
):
    with scope(event=event):
        event.feature_flags["show_featured"] = featured
        event.save()
        confirmed_submission.is_featured = True
        confirmed_submission.save()
    url = str(event.urls.featured)
    with django_assert_max_num_queries(9):
        response = client.get(url, follow=True)
    if featured == "never":
        assert response.status_code == 404
    else:
        assert response.status_code == 200
        url = url.replace("featured", "sneak")
        response = client.get(url)
        assert response.status_code == 301
        assert response.url == event.urls.featured


@pytest.mark.django_db
def test_featured_invisible_when_setting_unset(
    client, django_assert_max_num_queries, event, confirmed_submission
):
    with scope(event=event):
        event.feature_flags.pop("show_featured", None)
        event.save()
        confirmed_submission.is_featured = True
        confirmed_submission.save()
    with django_assert_max_num_queries(9):
        response = client.get(event.urls.featured, follow=True)
    assert response.status_code == 404


@pytest.mark.parametrize("featured", ("always", "never", "until_schedule", "after_schedule"))
@pytest.mark.django_db
def test_featured_invisible_because_schedule(
    client, django_assert_max_num_queries, event, featured
):
    with scope(event=event):
        event.feature_flags["show_featured"] = featured
        event.save()
        event.release_schedule("42")
    with django_assert_max_num_queries(8):
        response = client.get(event.urls.featured)

    if featured == "always":
        assert response.status_code == 200
    else:
        assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("featured", ("always", "after_schedule"))
def test_featured_visible_despite_schedule(
    client, django_assert_max_num_queries, event, featured
):
    event.feature_flags["show_featured"] = featured
    event.feature_flags["show_schedule"] = False
    event.save()
    with scope(event=event):
        event.release_schedule("42")
    with django_assert_max_num_queries(8):
        response = client.get(event.urls.featured, follow=True)
    assert response.status_code == 200
    assert "featured" in response.text


@pytest.mark.django_db
def test_featured_talk_list(
    client,
    django_assert_max_num_queries,
    event,
    confirmed_submission,
    other_confirmed_submission,
):
    confirmed_submission.is_featured = True
    confirmed_submission.save()

    event.feature_flags["show_featured"] = True
    event.save()

    with django_assert_max_num_queries(9):
        response = client.get(event.urls.featured, follow=True)
    assert response.status_code == 200
    content = response.text
    assert confirmed_submission.title in content
    assert other_confirmed_submission.title not in content


@pytest.mark.django_db
def test_featured_never_blocks_admin_mode_direct_url(client, event, administrator, confirmed_submission, monkeypatch):
    with scope(event=event):
        event.feature_flags['show_featured'] = 'never'
        event.save()
        confirmed_submission.is_featured = True
        confirmed_submission.save()

    monkeypatch.setattr(type(administrator), 'has_active_staff_session', lambda self, session_key: True)
    client.force_login(administrator)

    response = client.get(event.urls.featured)
    assert response.status_code == 404


VISIBILITY_MODES = (
    # show_featured value, visible before the first schedule publication, visible after it
    ("never", False, False),
    ("until_schedule", True, False),
    ("after_schedule", True, True),
    ("always", True, True),
)


def _prepare_featured_event(event, submission, featured):
    with scope(event=event):
        event.feature_flags["show_featured"] = featured
        # ``after_schedule`` additionally requires published talk pages once a schedule exists.
        event.talks_published = True
        event.save()
        submission.is_featured = True
        submission.save()


def _reloaded(event):
    return Event.objects.get(pk=event.pk)


@pytest.mark.django_db
@pytest.mark.parametrize("featured,before_release,after_release", VISIBILITY_MODES)
def test_featured_visibility_modes(event, confirmed_submission, featured, before_release, after_release):
    """All four visibility modes, before and after the first schedule publication."""
    _prepare_featured_event(event, confirmed_submission, featured)
    user = AnonymousUser()

    with scope(event=event):
        assert are_featured_submissions_visible(user, _reloaded(event)) is before_release
        event.release_schedule("1.0")
        assert are_featured_submissions_visible(user, _reloaded(event)) is after_release

    # Changing visibility must never drop the featured flag itself.
    confirmed_submission.refresh_from_db()
    assert confirmed_submission.is_featured is True


NAV_TAB_VISIBILITY_MODES = (
    # Same four modes, but the nav tab additionally requires featured content to be publicly
    # visible. The featured submission here is not scheduled, so once a schedule is published
    # only "always" (which short-circuits the content check) still shows the tab.
    ("never", False, False),
    ("until_schedule", True, False),
    ("after_schedule", True, False),
    ("always", True, True),
)


@pytest.mark.django_db
@pytest.mark.parametrize("featured,before_release,after_release", NAV_TAB_VISIBILITY_MODES)
def test_featured_nav_tab_visibility_modes(event, confirmed_submission, rf, featured, before_release, after_release):
    """The public nav tab follows the same four modes as the featured page itself."""
    _prepare_featured_event(event, confirmed_submission, featured)

    def nav_tab_visible():
        fresh = _reloaded(event)
        request = rf.get("/")
        request.event = fresh
        request.user = AnonymousUser()
        return can_view_featured_sessions_public({"request": request}, event=fresh)

    with scope(event=event):
        assert nav_tab_visible() is before_release
        event.release_schedule("1.0")
        assert nav_tab_visible() is after_release


@pytest.mark.django_db
def test_featured_until_schedule_reappears_when_switched_to_always(event, confirmed_submission):
    """Switching away from the teaser mode brings the same featured sessions back."""
    _prepare_featured_event(event, confirmed_submission, "until_schedule")
    user = AnonymousUser()

    with scope(event=event):
        event.release_schedule("1.0")
        assert are_featured_submissions_visible(user, _reloaded(event)) is False

        event.feature_flags["show_featured"] = "always"
        event.save()
        assert are_featured_submissions_visible(user, _reloaded(event)) is True
