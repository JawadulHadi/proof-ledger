import pytest

from core.models import Proof, Skill


@pytest.mark.django_db
def test_api_is_read_only(client):
    assert client.post('/api/v1/skills/', {'name': 'x'}).status_code == 405


@pytest.mark.django_db
def test_proof_endpoint_hides_private_interview_answers(client):
    skill = Skill.objects.create(name='NestJS', category='backend')
    proof = Proof.objects.create(title='gateway', kind='repo', star_answer='private')
    proof.skills.add(skill)
    body = client.get('/api/v1/proofs/').json()
    assert 'star_answer' not in str(body)


@pytest.mark.django_db
def test_summary_counts(client):
    Skill.objects.create(name='Redis', category='data')
    data = client.get('/api/v1/summary/').json()
    assert data['skills'] == 1 and data['unproven_skills'] == 1


@pytest.mark.django_db
def test_revise_requires_staff(client):
    skill = Skill.objects.create(name='Python', category='backend')
    assert client.post(f'/skills/{skill.pk}/revise/').status_code == 302


@pytest.mark.django_db
def test_funnel_endpoint(client):
    from core.models import Application, ResumeVariant
    v = ResumeVariant.objects.create(name='AI Engineer', headline='h')
    Application.objects.create(company='c', role='r', variant=v, status='replied')
    data = client.get('/api/v1/funnel/').json()
    assert data['variants'][0]['reply_rate'] == 1.0
    assert {'status': 'replied', 'label': 'Replied', 'n': 1} in data['stages']


@pytest.mark.django_db
def test_summary_is_cached(client):
    first = client.get('/api/v1/summary/').json()
    Skill.objects.create(name='Go', category='backend')
    assert client.get('/api/v1/summary/').json() == first
