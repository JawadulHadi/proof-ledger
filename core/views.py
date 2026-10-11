from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .dashboard import funnel, skills_with_freshness
from .models import Skill


def dashboard(request):
    skills = sorted(skills_with_freshness(), key=lambda s: s.fresh)
    return render(request, 'core/dashboard.html', {
        'skills': skills,
        'unproven_count': sum(1 for s in skills if s.proof_count == 0),
        'funnel': funnel(),
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def revise(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    skill.last_revised_at = timezone.now()
    skill.save(update_fields=['last_revised_at'])
    skill.fresh = skill.freshness()
    skill.proof_count = skill.proofs.count()
    return render(request, 'core/_skill_row.html', {'s': skill})
