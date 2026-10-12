import math
from collections import Counter
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
    skill.days = skill.days_idle()
    if skill.days is None:
        skill.n, skill.decay_rate = None, 0.0
        return skill
    exact = skill.days / skill.half_life_days
    # Map position from the same rounded freshness the tier and percent use, so a pin never
    # lands in a different band from its colour. Below 0.5% rounds to 0: fall back to exact.
    skill.n = math.log2(1 / skill.fresh) if skill.fresh else exact
    # Freshness points lost per day right now: the slope of the curve, d/dt of 100 * 0.5 ** (t/h).
    skill.decay_rate = round(100 * 0.5 ** exact * math.log(2) / skill.half_life_days, 2)
    return skill


# Half-life map geometry (SVG viewBox 0 0 640 250). In half-life units every skill sits on
# the same curve, freshness = 0.5 ** n, so the tier thresholds are the same vertical lines too.
MAP_X0, MAP_PER_HALF_LIFE, MAP_MAX_N = 44, 125, 4
MAP_FLATLINE_X = 600
MAP_PIN_GAP = 11
# Pins that fit in one flatline column between y=210 and y=30, and the columns either side of
# x=600 that still clear the divider at 572 and the viewBox edge at 640.
MAP_FLAT_ROWS = 17
MAP_FLAT_COLS = (0, -1, 1, -2, 2)


def map_x(n):
    return MAP_X0 + min(n, MAP_MAX_N) * MAP_PER_HALF_LIFE


def map_y(fresh):
    return 210 - fresh * 180


def half_life_map(skills):
    """Pins for every skill on the normalized decay curve, plus the curve and tier boundaries.

    Pins that would overlap are stacked upward (dy) so each stays hoverable. Skills with no
    revision and no proof have no position on the curve: they sit in a flatline column.
    """
    path = ' '.join(f'{"L" if i else "M"}{map_x(i / 10):.1f} {map_y(0.5 ** (i / 10)):.1f}'
                    for i in range(MAP_MAX_N * 10 + 1))
    placed, pins, flat = [], [], []
    for s in sorted(skills, key=lambda s: (s.n is None, s.n or 0)):
        if s.n is None:
            col, row = divmod(len(flat), MAP_FLAT_ROWS)
            x = MAP_FLATLINE_X + MAP_FLAT_COLS[col % len(MAP_FLAT_COLS)] * MAP_PIN_GAP
            flat.append({'skill': s, 'x': x, 'y': 210 - row * MAP_PIN_GAP, 'n': '', 'dy': 0})
            continue
        n = min(s.n, MAP_MAX_N)
        x, y = map_x(n), map_y(0.5 ** n)
        # Nearest free slot, alternating above and below the curve, kept inside the plot. A
        # column with every slot taken overlaps on the curve rather than failing the page.
        offsets = (k * sign * MAP_PIN_GAP for k in range(40) for sign in (-1, 1))
        dy = next((d for d in offsets if 30 <= y + d <= 210 and not any(
            abs(x - px) < MAP_PIN_GAP and abs(y + d - py) < MAP_PIN_GAP for px, py in placed)), 0)
        placed.append((x, y + dy))
        pins.append({'skill': s, 'x': round(x, 1), 'y': round(y + dy, 1), 'n': round(n, 3),
                     'dy': dy})
    # Band edges where freshness crosses the tier thresholds: 0.5 ** n == 0.6 and 0.5 ** n == 0.3.
    edges = [MAP_X0, map_x(math.log2(1 / 0.6)), map_x(math.log2(1 / 0.3)), map_x(MAP_MAX_N)]
    return {
        'path': path,
        'area': f'{path} L{map_x(MAP_MAX_N)} 210 L{MAP_X0} 210 Z',
        'bands': [{'tier': t, 'x': round(a, 1), 'width': round(b - a, 1)}
                  for t, a, b in zip(['fresh', 'fading', 'stale'], edges, edges[1:], strict=False)],
        'ticks': [{'n': n, 'x': map_x(n)} for n in range(MAP_MAX_N + 1)],
        'pins': pins + flat,
        'flatline': len(flat),
    }


def decay_outlook(skills):
    """Total freshness points the ledger loses per day, and the skill losing them fastest."""
    fading = [s for s in skills if s.decay_rate > 0]
    return {
        'per_day': round(sum(s.decay_rate for s in fading), 2),
        'fastest': max(fading, key=lambda s: s.decay_rate) if fading else None,
    }


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
    # Every proof, newest first: the page shows the first few and expands to the rest.
    # star_answer is private and never rendered, so it stays in the database.
    proofs = list(Proof.objects.defer('star_answer').prefetch_related('skills')
                  .order_by('-occurred_at'))
    kinds = Counter(p.kind for p in proofs)
    return {
        'skills': skills,
        'stale_skills': skills[:5],
        'unproven': [s for s in skills if s.proof_count == 0],
        'stats': summary(skills),
        'map': half_life_map(skills),
        'decay': decay_outlook(skills),
        'funnel': stages,
        'variants': variant_funnel(),
        'proofs': proofs,
        'proof_kinds': [{'kind': k, 'label': label, 'n': kinds[k]}
                        for k, label in Proof.Kind.choices if kinds.get(k)],
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
