import httpx
from django.core.management.base import BaseCommand

from core.models import Proof


def is_alive(client, url):
    try:
        resp = client.head(url)
        if resp.status_code in (405, 403):  # some hosts refuse HEAD; ask again with GET
            resp = client.get(url)
        return resp.status_code < 400
    except httpx.HTTPError:
        return False


class Command(BaseCommand):
    help = 'Check every proof URL and flag dead links (sets Proof.link_ok).'

    def handle(self, *args, **options):
        proofs = Proof.objects.exclude(url='')
        dead = []
        with httpx.Client(timeout=10, follow_redirects=True,
                          headers={'User-Agent': 'proof-ledger-link-check'}) as client:
            for proof in proofs:
                ok = is_alive(client, proof.url)
                if ok != proof.link_ok:
                    proof.link_ok = ok
                    proof.save(update_fields=['link_ok'])
                if not ok:
                    dead.append(proof)
        for proof in dead:
            self.stdout.write(self.style.WARNING(f'dead: {proof.title} {proof.url}'))
        self.stdout.write(f'Checked {proofs.count()} links, {len(dead)} dead')
