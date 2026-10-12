import os

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from core.models import Proof, Skill

PER_PAGE = 100
MAX_PAGES = 10


def topic_index():
    """Map each GitHub topic to the skills it proves (skill name or one of its github_topics)."""
    index = {}
    for skill in Skill.objects.all():
        for topic in skill.topic_list():
            index.setdefault(topic, []).append(skill)
    return index


class Command(BaseCommand):
    help = 'Sync public GitHub repos into Proof rows and link skills by repo topic.'

    def add_arguments(self, parser):
        parser.add_argument('--include-forks', action='store_true',
                            help='Forks are skipped by default: they prove nothing you built.')

    def handle(self, *args, **options):
        headers = {'Accept': 'application/vnd.github+json'}
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = f'Bearer {token}'
        url = f'https://api.github.com/users/{settings.GITHUB_USER}/repos'
        repos = []
        # GitHub pages at 100 repos; keep going until a short page (capped at 1,000 repos).
        for page in range(1, MAX_PAGES + 1):
            try:
                resp = httpx.get(url, params={'per_page': PER_PAGE, 'sort': 'pushed', 'page': page},
                                 headers=headers, timeout=20)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise CommandError(f'GitHub sync failed: {exc}') from exc
            batch = resp.json()
            repos.extend(batch)
            if len(batch) < PER_PAGE:
                break

        index = topic_index()
        synced = linked = 0
        for repo in repos:
            if repo.get('archived') or (repo.get('fork') and not options['include_forks']):
                continue
            proof, _ = Proof.objects.update_or_create(
                url=repo['html_url'],
                defaults={
                    'title': repo['name'],
                    'kind': Proof.Kind.REPO,
                    'occurred_at': parse_datetime(repo['pushed_at']),
                },
            )
            # Topics plus the repo's primary language: a TypeScript repo proves TypeScript.
            topics = list(repo.get('topics') or [])
            if repo.get('language'):
                topics.append(repo['language'].lower().replace(' ', '-'))
            skills = {s.pk: s for topic in topics for s in index.get(topic, [])}
            if skills:
                proof.skills.add(*skills.values())
                linked += len(skills)
            synced += 1
        self.stdout.write(self.style.SUCCESS(f'Synced {synced} repos, {linked} skill links'))
