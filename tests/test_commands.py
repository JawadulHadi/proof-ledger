from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from core.models import Proof, Skill


@pytest.mark.django_db
def test_seed_and_digest():
    call_command('seed_demo', stdout=StringIO())
    out = StringIO()
    call_command('weekly_digest', stdout=out)
    assert '# Weekly plan' in out.getvalue()
    assert Skill.objects.filter(name='Python').exists()


@pytest.mark.django_db
def test_sync_github_links_skills_by_topic():
    Skill.objects.create(name='FastAPI', category='backend')
    fake = MagicMock()
    fake.json.return_value = [{
        'html_url': 'https://github.com/x/demo', 'name': 'demo',
        'pushed_at': '2026-01-01T00:00:00Z', 'topics': ['fastapi'],
    }]
    with patch('core.management.commands.sync_github.httpx.get', return_value=fake):
        call_command('sync_github', stdout=StringIO())
    proof = Proof.objects.get(title='demo')
    assert list(proof.skills.values_list('name', flat=True)) == ['FastAPI']


@pytest.mark.django_db
def test_staff_can_revise_via_htmx(client, django_user_model):
    user = django_user_model.objects.create_user('s', 's@example.com', 'pw', is_staff=True)
    client.force_login(user)
    skill = Skill.objects.create(name='Django', category='backend')
    resp = client.post(f'/skills/{skill.pk}/revise/')
    assert resp.status_code == 200
    skill.refresh_from_db()
    assert skill.last_revised_at is not None


@pytest.mark.django_db
def test_public_dashboard_renders(client):
    Skill.objects.create(name='Redis', category='data')
    assert client.get('/').status_code == 200
