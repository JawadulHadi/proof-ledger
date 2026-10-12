from datetime import date, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

import httpx
import pytest
from django.core.management import call_command

from core.dashboard import funnel, save_snapshot, variant_funnel, week_start
from core.models import Application, MetricSnapshot, Proof, ResumeVariant, Skill


@pytest.fixture
def variants():
    lead = ResumeVariant.objects.create(name='Backend Lead', headline='h')
    ai = ResumeVariant.objects.create(name='AI Engineer', headline='h')
    for status in ['applied', 'replied', 'interview', 'saved']:
        Application.objects.create(company='c', role='r', variant=lead, status=status)
    Application.objects.create(company='c', role='r', variant=ai, status='rejected')
    return lead, ai


@pytest.mark.django_db
def test_variant_funnel_counts_replies_per_resume(variants):
    rows = {r['variant']: r for r in variant_funnel()}
    # saved is not sent; replied and interview both count as a response
    assert rows['Backend Lead'] == {'variant': 'Backend Lead', 'sent': 3, 'responded': 2,
                                    'interviews': 1, 'reply_rate': 0.67}
    assert rows['AI Engineer']['reply_rate'] == 0.0


@pytest.mark.django_db
def test_funnel_is_in_pipeline_order(variants):
    stages = [row['status'] for row in funnel()]
    assert stages == ['saved', 'applied', 'replied', 'interview', 'offer', 'rejected']


@pytest.mark.django_db
def test_snapshot_counts_only_this_week():
    monday = week_start(date(2026, 10, 14))
    assert monday == date(2026, 10, 12)
    Application.objects.create(company='a', role='r', status='replied', referral=True,
                               applied_on=monday)
    Application.objects.create(company='b', role='r', status='applied',
                               applied_on=monday - timedelta(days=1))
    snap = save_snapshot(monday)
    assert (snap.applications, snap.replies, snap.referral_asks) == (1, 1, 1)
    save_snapshot(monday)  # idempotent: one row per week
    assert MetricSnapshot.objects.count() == 1


@pytest.mark.django_db
def test_weekly_digest_lists_variants_and_saves(variants):
    Skill.objects.create(name='RAG', category='ai')
    out = StringIO()
    call_command('weekly_digest', '--save', stdout=out)
    text = out.getvalue()
    assert 'Backend Lead: 2/3 (67%)' in text
    assert 'Ship or link one proof for RAG' in text
    assert MetricSnapshot.objects.exists()


@pytest.mark.django_db
def test_sync_github_uses_topic_aliases_and_skips_forks():
    llm = Skill.objects.create(name='LLM integration', category='ai', github_topics='llm, agents')
    fake = MagicMock()
    fake.json.return_value = [
        {'html_url': 'https://github.com/x/a', 'name': 'a', 'pushed_at': '2026-01-01T00:00:00Z',
         'topics': ['llm', 'agents'], 'fork': False},
        {'html_url': 'https://github.com/x/f', 'name': 'f', 'pushed_at': '2026-01-01T00:00:00Z',
         'topics': ['llm'], 'fork': True},
    ]
    with patch('core.management.commands.sync_github.httpx.get', return_value=fake):
        call_command('sync_github', stdout=StringIO())
    assert list(Proof.objects.values_list('title', flat=True)) == ['a']
    assert list(llm.proofs.values_list('title', flat=True)) == ['a']


@pytest.mark.django_db
def test_link_check_flags_dead_links():
    good = Proof.objects.create(title='good', kind='repo', url='https://ok.test/')
    bad = Proof.objects.create(title='bad', kind='repo', url='https://gone.test/')
    down = Proof.objects.create(title='down', kind='repo', url='https://down.test/')

    def handler(request):
        if request.url.host == 'down.test':
            raise httpx.ConnectError('no route')
        if request.method == 'HEAD' and request.url.host == 'ok.test':
            return httpx.Response(405)  # HEAD refused, GET works
        return httpx.Response(200 if request.url.host == 'ok.test' else 404)

    real_client = httpx.Client
    with patch('core.management.commands.link_check.httpx.Client',
               lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
        out = StringIO()
        call_command('link_check', stdout=out)
    for p in (good, bad, down):
        p.refresh_from_db()
    assert (good.link_ok, bad.link_ok, down.link_ok) == (True, False, False)
    assert '2 dead' in out.getvalue()


@pytest.mark.django_db
def test_dashboard_shows_unproven_banner_and_proofs(client, variants):
    Skill.objects.create(name='GraphQL', category='backend')
    Proof.objects.create(title='gateway', kind='repo', url='https://example.com', link_ok=False)
    html = client.get('/').content.decode()
    assert 'without proof' in html and 'GraphQL' in html
    assert 'link dead' in html
    assert 'Backend Lead' in html


@pytest.mark.django_db
def test_half_life_map_survives_a_crowded_column():
    from django.utils import timezone

    from core.dashboard import half_life_map, skills_with_freshness

    # More pins than fit in one column (17 slots), both on the curve and in the flatline.
    for i in range(25):
        Skill.objects.create(name=f'Today {i}', category='x', last_revised_at=timezone.now())
        Skill.objects.create(name=f'Never {i}', category='x')
    data = half_life_map(skills_with_freshness())

    assert len(data['pins']) == 50 and data['flatline'] == 25
    assert all(30 <= p['y'] <= 210 for p in data['pins'])
    assert all(572 < p['x'] < 640 for p in data['pins'] if p['n'] == '')


@pytest.mark.django_db
def test_half_life_map_places_skills_on_one_curve():
    from datetime import timedelta as td

    from django.utils import timezone

    from core.dashboard import half_life_map, map_x, map_y, skills_with_freshness

    now = timezone.now()
    # 90 days on a 90-day half-life and 30 days on a 30-day half-life: both one half-life idle.
    Skill.objects.create(name='Slow', category='x', half_life_days=90,
                         last_revised_at=now - td(days=90))
    Skill.objects.create(name='Quick', category='x', half_life_days=30,
                         last_revised_at=now - td(days=30))
    Skill.objects.create(name='Never', category='x')
    data = half_life_map(skills_with_freshness())
    pins = {p['skill'].name: p for p in data['pins']}

    assert pins['Slow']['n'] == pins['Quick']['n'] == 1
    assert pins['Slow']['x'] == pins['Quick']['x'] == map_x(1)
    # The second pin on the same spot is stacked upward so both stay clickable.
    assert sorted([pins['Slow']['dy'], pins['Quick']['dy']]) == [-11, 0]
    assert min(pins['Slow']['y'], pins['Quick']['y']) == map_y(0.5) - 11
    # No revision and no proof: off the curve, in the flatline column.
    assert pins['Never']['n'] == '' and data['flatline'] == 1
    # Tier bands start where freshness crosses 0.6 and 0.3, the same for every half-life.
    fresh, fading, stale = data['bands']
    assert fresh['x'] + fresh['width'] == fading['x'] == round(map_x(0.737), 1)
    assert stale['x'] + stale['width'] == map_x(4)


@pytest.mark.django_db
def test_decay_outlook_names_the_fastest_fading_skill():
    from django.utils import timezone

    from core.dashboard import decay_outlook, skills_with_freshness

    now = timezone.now()
    Skill.objects.create(name='Short', category='x', half_life_days=30, last_revised_at=now)
    Skill.objects.create(name='Long', category='x', half_life_days=180, last_revised_at=now)
    Skill.objects.create(name='Never', category='x')
    out = decay_outlook(skills_with_freshness())
    # At full freshness the slope is 100 * ln2 / half-life points a day.
    assert out['fastest'].name == 'Short'
    assert out['per_day'] == round(2.31 + 0.39, 2)


@pytest.mark.django_db
def test_dashboard_renders_map_and_ticker(client):
    Skill.objects.create(name='GraphQL', category='backend')
    html = client.get('/').content.decode()
    assert 'id="hlmap"' in html and 'pin stale flat' in html
    assert 'id="ticker"' in html


@pytest.mark.django_db
def test_dashboard_lists_every_proof_not_just_recent(client):
    for i in range(14):
        Proof.objects.create(title=f'repo-{i}', kind='repo')
    Proof.objects.create(title='latency-case', kind='case')
    html = client.get('/').content.decode()
    assert all(f'>repo-{i}<' in html or f'repo-{i}\n' in html for i in range(14))
    assert 'Show all 15' in html
    assert 'Case study <span>1</span>' in html
