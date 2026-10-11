import os

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from core.models import Proof, Skill


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
        try:
            resp = httpx.get(url, params={'per_page': 100, 'sort': 'pushed'}, headers=headers,
                             timeout=20)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise CommandError(f'GitHub sync failed: {exc}') from exc

        index = topic_index()
        synced = linked = 0
        for repo in resp.json():
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
            skills = {s.pk: s for topic in repo.get('topics', []) for s in index.get(topic, [])}
            if skills:
                proof.skills.add(*skills.values())
                linked += len(skills)
            synced += 1
        self.stdout.write(self.style.SUCCESS(f'Synced {synced} repos, {linked} skill links'))
