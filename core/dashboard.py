from datetime import timedelta

from django.db.models import Count, Max, Q
from django.utils import timezone

from .models import Application, MetricSnapshot, Proof, ResumeVariant, Skill

# Statuses that mean the company answered (anything past "applied").
RESPONDED = [Application.Status.REPLIED, Application.Status.INTERVIEW, Application.Status.OFFER]
FUNNEL_ORDER = [s for s, _ in Application.Status.choices]


def tier(value):
    return 'fresh' if value >= 0.6 else 'fading' if value >= 0.3 else 'stale'


def decorate(skill):
    """Attach display values used by the dashboard, the admin home and the HTMX row."""
    skill.fresh = skill.freshness()
    skill.pct = round(skill.fresh * 100)
    skill.tier = tier(skill.fresh)
    return skill


def skills_with_freshness():
    qs = Skill.objects.annotate(
        last_proof=Max('proofs__occurred_at'),
        proof_count=Count('proofs', distinct=True),
    )
    return [decorate(skill) for skill in qs]


def funnel():
    """Application counts per status, in pipeline order, including empty stages."""
    counts = dict(Application.objects.values_list('status').annotate(n=Count('id')))
    labels = dict(Application.Status.choices)
    return [{'status': s, 'label': labels[s], 'n': counts.get(s, 0)} for s in FUNNEL_ORDER
            if counts.get(s) or s != Application.Status.SAVED]


def variant_funnel():
    """Which resume variant gets answers: sent, responded, interviews and reply rate per variant."""
    sent = ~Q(applications__status=Application.Status.SAVED)
    rows = ResumeVariant.objects.annotate(
        sent=Count('applications', filter=sent),
        responded=Count('applications', filter=Q(applications__status__in=RESPONDED)),
        interviews=Count('applications', filter=Q(
            applications__status__in=[Application.Status.INTERVIEW, Application.Status.OFFER])),
    ).order_by('name')
    out = []
    for v in rows:
        rate = round(v.responded / v.sent, 2) if v.sent else 0.0
        out.append({'variant': v.name, 'sent': v.sent, 'responded': v.responded,
                    'interviews': v.interviews, 'reply_rate': rate})
    return out


def week_start(day=None):
    day = day or timezone.localdate()
    return day - timedelta(days=day.weekday())


def week_metrics(start):
    """Numbers for the week starting on `start` (a Monday), from applications sent that week."""
    end = start + timedelta(days=7)
    week = Application.objects.filter(applied_on__gte=start, applied_on__lt=end)
    return {
        'applications': week.count(),
        'replies': week.filter(status__in=RESPONDED).count(),
        'interviews': week.filter(
            status__in=[Application.Status.INTERVIEW, Application.Status.OFFER]).count(),
        'referral_asks': week.filter(referral=True).count(),
    }


def save_snapshot(start=None):
    start = start or week_start()
    snap, _ = MetricSnapshot.objects.update_or_create(
        week_start=start, defaults=week_metrics(start))
    return snap


def summary(skills=None):
    skills = skills if skills is not None else skills_with_freshness()
    return {
        'skills': len(skills),
        'unproven_skills': sum(1 for s in skills if s.proof_count == 0),
        'stale_skills': sum(1 for s in skills if s.fresh < 0.3),
        'proofs': Proof.objects.count(),
        'dead_links': Proof.objects.filter(link_ok=False).count(),
        'applications': Application.objects.exclude(status=Application.Status.SAVED).count(),
    }


def dashboard_context():
    skills = sorted(skills_with_freshness(), key=lambda s: s.fresh)
    stages = funnel()
    top = max([row['n'] for row in stages] or [0]) or 1
    for row in stages:
        row['pct'] = round(100 * row['n'] / top)
    return {
        'skills': skills,
        'stale_skills': skills[:5],
        'unproven': [s for s in skills if s.proof_count == 0],
        'stats': summary(skills),
        'funnel': stages,
        'variants': variant_funnel(),
        'recent_proofs': Proof.objects.prefetch_related('skills').order_by('-occurred_at')[:6],
        'snapshots': list(MetricSnapshot.objects.all()[:8]),
    }


def dashboard_callback(request, context):
    data = dashboard_context()
    stats = data['stats']
    data['stat_tiles'] = [
        (stats['skills'], 'skills tracked'), (stats['proofs'], 'proofs linked'),
        (stats['stale_skills'], 'stale skills'), (stats['dead_links'], 'dead proof links'),
    ]
    context.update(data)
    return context
