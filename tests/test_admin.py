import pytest
from django.urls import reverse

from core.models import Proof, Skill


@pytest.fixture
def staff_client(client, django_user_model):
    user = django_user_model.objects.create_superuser('boss', 'boss@example.com', 'pw')
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_admin_index_renders(staff_client):
    assert staff_client.get('/admin/').status_code == 200


@pytest.mark.django_db
def test_changelist_has_no_n_plus_one(staff_client, django_assert_max_num_queries):
    for i in range(10):
        skill = Skill.objects.create(name=f'skill{i}', category='backend')
        proof = Proof.objects.create(title=f'proof{i}', kind='repo')
        proof.skills.add(skill)
    with django_assert_max_num_queries(15):
        assert staff_client.get(reverse('admin:core_skill_changelist')).status_code == 200


@pytest.mark.django_db
def test_mark_revised_action(staff_client):
    skill = Skill.objects.create(name='Django', category='backend')
    staff_client.post(
        reverse('admin:core_skill_changelist'),
        {'action': 'mark_revised', '_selected_action': [skill.pk]},
    )
    skill.refresh_from_db()
    assert skill.last_revised_at is not None
