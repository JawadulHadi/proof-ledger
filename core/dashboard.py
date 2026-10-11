from django.db.models import Count, Max

from .models import Application, Skill


def skills_with_freshness():
    qs = Skill.objects.annotate(
        last_proof=Max('proofs__occurred_at'),
        proof_count=Count('proofs', distinct=True),
    )
    skills = list(qs)
    for skill in skills:
        skill.fresh = skill.freshness()
    return skills


def funnel():
    return list(Application.objects.values('status').annotate(n=Count('id')).order_by('status'))


def dashboard_callback(request, context):
    skills = skills_with_freshness()
    context.update({
        'stale_skills': sorted(skills, key=lambda s: s.fresh)[:5],
        'unproven': [s for s in skills if s.proof_count == 0],
        'funnel': funnel(),
    })
    return context
