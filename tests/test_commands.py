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
    # The swapped-in row is marked so the dashboard plays the revive animation.
    assert 'class="row revived"' in resp.content.decode()
    assert 'data-pct="100"' in resp.content.decode()
    skill.refresh_from_db()
    assert skill.last_revised_at is not None


@pytest.mark.django_db
def test_public_dashboard_renders(client):
    Skill.objects.create(name='Redis', category='data')
    assert client.get('/').status_code == 200


@pytest.mark.django_db
def test_sync_github_pages_through_every_repo_and_links_by_language():
    ts = Skill.objects.create(name='TypeScript', category='backend')

    def page(n, count, **extra):
        fake = MagicMock()
        fake.json.return_value = [
            {'html_url': f'https://github.com/x/p{n}-{i}', 'name': f'p{n}-{i}',
             'pushed_at': '2026-01-01T00:00:00Z', 'topics': [], 'fork': False, **extra}
            for i in range(count)]
        return fake

    # A full first page means there may be more; the short second page ends the loop.
    pages = [page(1, 100), page(2, 3, language='TypeScript')]
    with patch('core.management.commands.sync_github.httpx.get', side_effect=pages) as get:
        call_command('sync_github', stdout=StringIO())
    assert [c.kwargs['params']['page'] for c in get.call_args_list] == [1, 2]
    assert Proof.objects.count() == 103
    assert ts.proofs.count() == 3


def _repo(name, owner='JawadulHadi', **extra):
    return {'html_url': f'https://github.com/{owner}/{name}', 'name': name,
            'owner': {'login': owner}, 'pushed_at': '2026-01-01T00:00:00Z', 'topics': [],
            'fork': False, **extra}


def _response(repos):
    fake = MagicMock()
    fake.json.return_value = repos
    return fake


@pytest.mark.django_db
def test_sync_github_with_token_counts_private_and_ignores_other_owners(monkeypatch, settings):
    settings.GITHUB_USER = 'JawadulHadi'
    monkeypatch.setenv('GITHUB_TOKEN', 't')
    repos = [_repo('public-one'), _repo('private-one', private=True),
             _repo('theirs', owner='someone')]
    out = StringIO()
    with patch('core.management.commands.sync_github.httpx.get',
               return_value=_response(repos)) as get:
        call_command('sync_github', stdout=out)
    # The authenticated endpoint is the one that includes private repos.
    assert get.call_args.args[0] == 'https://api.github.com/user/repos'
    assert get.call_args.kwargs['params']['visibility'] == 'all'
    assert sorted(Proof.objects.values_list('title', flat=True)) == ['private-one', 'public-one']
    assert 'Synced 2 (1 private)' in out.getvalue()


@pytest.mark.django_db
def test_sync_github_reports_skipped_forks_and_archived(monkeypatch):
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    repos = [_repo('mine'), _repo('forked', fork=True), _repo('old', archived=True)]
    out = StringIO()
    with patch('core.management.commands.sync_github.httpx.get', return_value=_response(repos)):
        call_command('sync_github', stdout=out)
    assert list(Proof.objects.values_list('title', flat=True)) == ['mine']
    assert 'Skipped 1 forks and 1 archived' in out.getvalue()
    assert 'public only' in out.getvalue()

    with patch('core.management.commands.sync_github.httpx.get', return_value=_response(repos)):
        call_command('sync_github', '--include-archived', '--include-forks', stdout=StringIO())
    assert Proof.objects.count() == 3


@pytest.mark.django_db
def test_sync_github_prune_removes_only_this_users_vanished_repos(monkeypatch, settings):
    settings.GITHUB_USER = 'JawadulHadi'
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    Proof.objects.create(title='renamed-away', kind=Proof.Kind.REPO,
                         url='https://github.com/JawadulHadi/renamed-away')
    Proof.objects.create(title='someone else', kind=Proof.Kind.REPO,
                         url='https://github.com/someone/thing')
    Proof.objects.create(title='a talk', kind=Proof.Kind.CASE,
                         url='https://github.com/JawadulHadi/talk')
    with patch('core.management.commands.sync_github.httpx.get',
               return_value=_response([_repo('kept')])):
        call_command('sync_github', stdout=StringIO())
    assert Proof.objects.filter(title='renamed-away').exists()  # no --prune: nothing deleted

    out = StringIO()
    with patch('core.management.commands.sync_github.httpx.get',
               return_value=_response([_repo('kept')])):
        call_command('sync_github', '--prune', stdout=out)
    titles = sorted(Proof.objects.values_list('title', flat=True))
    assert titles == ['a talk', 'kept', 'someone else']
    assert 'Pruned 1 stale' in out.getvalue()
