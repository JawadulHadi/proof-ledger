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
