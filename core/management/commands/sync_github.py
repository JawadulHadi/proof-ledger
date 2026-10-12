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


def fetch_repos(user, token):
    """Every repo GITHUB_USER owns.

    With a token, /user/repos lists the token owner's repos including private ones; it is filtered
    to GITHUB_USER so a token belonging to someone else can't pull in their repos. Without a token,
    only public repos are visible.
    """
    headers = {'Accept': 'application/vnd.github+json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
        url = 'https://api.github.com/user/repos'
        params = {'affiliation': 'owner', 'visibility': 'all'}
    else:
        url = f'https://api.github.com/users/{user}/repos'
        params = {}
    repos = []
    # GitHub pages at 100 repos; keep going until a short page (capped at 1,000 repos).
    for page in range(1, MAX_PAGES + 1):
        try:
            resp = httpx.get(url, params={**params, 'per_page': PER_PAGE, 'sort': 'pushed',
                                          'page': page}, headers=headers, timeout=20)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise CommandError(f'GitHub sync failed: {exc}') from exc
        batch = resp.json()
        repos.extend(batch)
        if len(batch) < PER_PAGE:
            break
    if token:
        repos = [r for r in repos
                 if (r.get('owner') or {}).get('login', '').lower() == user.lower()]
    return repos


class Command(BaseCommand):
    help = 'Sync GitHub repos into Proof rows and link skills by repo topic.'

    def add_arguments(self, parser):
        parser.add_argument('--include-forks', action='store_true',
                            help='Forks are skipped by default: they prove nothing you built.')
        parser.add_argument('--include-archived', action='store_true',
                            help='Archived repos are skipped by default.')
        parser.add_argument('--prune', action='store_true',
                            help="Delete repo proofs for GITHUB_USER that GitHub no longer lists "
                                 "(renamed or deleted repos). Off by default.")

    def handle(self, *args, **options):
        user = settings.GITHUB_USER
        token = os.environ.get('GITHUB_TOKEN')
        repos = fetch_repos(user, token)

        index = topic_index()
        synced = linked = private = forks = archived = 0
        seen = set()
        for repo in repos:
            seen.add(repo['html_url'])
            if repo.get('fork') and not options['include_forks']:
                forks += 1
                continue
            if repo.get('archived') and not options['include_archived']:
                archived += 1
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
            private += bool(repo.get('private'))

        pruned = 0
        if options['prune']:
            stale = (Proof.objects.filter(kind=Proof.Kind.REPO,
                                          url__istartswith=f'https://github.com/{user}/')
                     .exclude(url__in=seen))
            pruned = stale.count()
            stale.delete()

        scope = ('public and private' if token
                 else 'public only; set GITHUB_TOKEN to include private')
        self.stdout.write(self.style.SUCCESS(
            f'Found {len(repos)} repos for {user} ({scope}). Synced {synced} '
            f'({private} private), {linked} skill links. Skipped {forks} forks and {archived} '
            f'archived.' + (f' Pruned {pruned} stale.' if options['prune'] else '')))
