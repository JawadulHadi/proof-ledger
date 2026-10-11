from django.core.management.base import BaseCommand

from core.dashboard import funnel, save_snapshot, skills_with_freshness, variant_funnel


class Command(BaseCommand):
    help = 'Print a markdown weekly plan: stale and unproven skills, funnel, next actions.'

    def add_arguments(self, parser):
        parser.add_argument('--save', action='store_true',
                            help="Also store this week's numbers as a MetricSnapshot.")

    def handle(self, *args, **options):
        skills = sorted(skills_with_freshness(), key=lambda s: s.fresh)
        unproven = [s for s in skills if s.proof_count == 0]
        lines = ['# Weekly plan', '', '## Revise these first']
        lines += [f'- {s.name} (freshness {s.fresh})' for s in skills[:5]] or ['- no skills yet']
        lines += ['', '## Need proof']
        lines += [f'- {s.name}' for s in unproven] or ['- none']
        lines += ['', '## Funnel']
        lines += [f"- {row['label']}: {row['n']}" for row in funnel() if row['n']] \
            or ['- no applications yet']
        variants = [v for v in variant_funnel() if v['sent']]
        if variants:
            lines += ['', '## Reply rate by resume variant']
            lines += [f"- {v['variant']}: {v['responded']}/{v['sent']} ({v['reply_rate']:.0%})"
                      for v in variants]
        lines += ['', '## Next actions']
        lines += [f'- Write a revision note for {s.name}' for s in skills[:2]]
        lines += [f'- Ship or link one proof for {s.name}' for s in unproven[:2]]
        if options['save']:
            snap = save_snapshot()
            lines += ['', f'Saved snapshot for week of {snap.week_start}.']
        self.stdout.write('\n'.join(lines))
