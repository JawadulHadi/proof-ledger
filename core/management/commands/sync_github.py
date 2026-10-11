import os

import httpx
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from core.models import Proof, Skill


class Command(BaseCommand):
    help = 'Sync public GitHub repos into Proof rows and link skills by repo topic.'

    def handle(self, *args, **options):
        headers = {'Accept': 'application/vnd.github+json'}
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = f'Bearer {token}'
        url = f'https://api.github.com/users/{settings.GITHUB_USER}/repos'
        try:
            resp = httpx.get(url, params={'per_page': 100}, headers=headers, timeout=20)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise CommandError(f'GitHub sync failed: {exc}') from exc

        synced = 0
        for repo in resp.json():
            proof, _ = Proof.objects.update_or_create(
                url=repo['html_url'],
                defaults={
                    'title': repo['name'],
                    'kind': Proof.Kind.REPO,
                    'occurred_at': parse_datetime(repo['pushed_at']),
                },
            )
            for topic in repo.get('topics', []):
                skill = Skill.objects.filter(name__iexact=topic.replace('-', ' ')).first()
                if skill:
                    proof.skills.add(skill)
            synced += 1
        self.stdout.write(self.style.SUCCESS(f'Synced {synced} repos'))
