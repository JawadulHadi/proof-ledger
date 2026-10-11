from django.core.management.base import BaseCommand

from core.dashboard import funnel, skills_with_freshness


class Command(BaseCommand):
    help = 'Print a markdown plan for the week: stale skills, unproven skills, funnel.'

    def handle(self, *args, **options):
        skills = sorted(skills_with_freshness(), key=lambda s: s.fresh)
        lines = ['# Weekly plan', '', '## Revise these first']
        lines += [f'- {s.name} (freshness {s.fresh})' for s in skills[:5]]
        lines += ['', '## Need proof']
        lines += [f'- {s.name}' for s in skills if s.proof_count == 0] or ['- none']
        lines += ['', '## Funnel']
        lines += [f"- {row['status']}: {row['n']}" for row in funnel()] or ['- no applications yet']
        self.stdout.write('\n'.join(lines))
