from django.core.management.base import BaseCommand

from core.models import Application, ResumeVariant, Skill

SKILLS = [
    ('Python', 'backend'), ('FastAPI', 'backend'), ('Django', 'backend'),
    ('NestJS', 'backend'), ('TypeScript', 'backend'), ('PostgreSQL', 'data'),
    ('GraphQL', 'backend'), ('BullMQ', 'backend'), ('Redis', 'data'),
    ('RAG', 'ai'), ('LLM integration', 'ai'), ('React', 'frontend'),
]


class Command(BaseCommand):
    help = 'Create demo data. Edit levels to match reality, the dashboard is only as honest as you.'

    def handle(self, *args, **options):
        for name, category in SKILLS:
            Skill.objects.get_or_create(name=name, defaults={'category': category})
        variants = [
            ResumeVariant.objects.get_or_create(name=n, defaults={'headline': h})[0]
            for n, h in [
                ('Backend Lead', 'Backend Lead and Architect'),
                ('AI Engineer', 'AI/LLM Engineer, provider-agnostic systems'),
                ('Senior Backend', 'Senior Backend Engineer'),
            ]
        ]
        if not Application.objects.exists():
            Application.objects.create(company='Example Co', role='Backend Lead',
                                       variant=variants[0], status='applied')
        self.stdout.write(self.style.SUCCESS('Seeded'))
