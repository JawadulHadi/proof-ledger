from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .dashboard import dashboard_context, decorate
from .models import Skill


def dashboard(request):
    return render(request, 'core/dashboard.html', dashboard_context())


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def revise(request, pk):
    skill = get_object_or_404(Skill, pk=pk)
    skill.last_revised_at = timezone.now()
    skill.save(update_fields=['last_revised_at'])
    skill.proof_count = skill.proofs.count()
    decorate(skill)
    return render(request, 'core/_skill_row.html', {'s': skill})
