from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

from core.models import Skill

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.django_db
def test_freshness_halves_every_half_life():
    skill = Skill.objects.create(
        name='Python', category='backend', half_life_days=90, last_revised_at=BASE
    )
    with freeze_time(BASE):
        assert skill.freshness() == 1.0
    with freeze_time(BASE + timedelta(days=90)):
        assert skill.freshness() == 0.5
    with freeze_time(BASE + timedelta(days=180)):
        assert skill.freshness() == 0.25


@pytest.mark.django_db
def test_skill_without_activity_is_zero():
    assert Skill.objects.create(name='Redis', category='data').freshness() == 0.0
